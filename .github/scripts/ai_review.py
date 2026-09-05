#!/usr/bin/env python3
"""
Sovereign ULA — AI Agent PR Review Runner (agentic: reviews AND fixes).

FREE-ENDPOINT POLICY: this runner only talks to free-tier / OpenAI-compatible
endpoints. No OpenAI. Providers, tried in order of the first key present:
  NVIDIA NIM        NVIDIA_API_KEY       integrate.api.nvidia.com
  Google Gemini     GEMINI_API_KEY       generativelanguage.googleapis.com (OpenAI-compat layer)
  Groq              GROQ_API_KEY         api.groq.com
  OpenRouter        OPENROUTER_API_KEY   openrouter.ai   (":free" model default)
  HuggingFace       HF_TOKEN             router.huggingface.co

Flow:
  1. Fetch the PR diff (raw patch, with a paginated-files fallback past the
     300-file whole-diff cap) + metadata.
  2. Send the diff to the LLM for INLINE findings. Each finding:
     {path, line, severity, comment} where `comment` embeds a
     ```suggestion ... ``` block with the exact replacement code.
  3. AGENTIC STEP: for every critical/warning finding, patch the real source
     file at the reported line (the diff's new-file line == current file line),
     commit the change, and PUSH it back to the PR branch. A real fix, not a
     comment.
  4. Post ONE short summary comment listing what was auto-fixed (or that the
     diff was clean). The caller (ai-agent-review.yml) gates the merge on the
     SOVEREIGN_RESULT marker printed at the end.

Env:
  GITHUB_TOKEN, REPO, PR_NUMBER   — provided by Actions
  LLM_MODEL                       — optional model override (else provider default)
  LLM_BASE_URL                    — optional endpoint override (forces first
                                    configured provider onto this URL)
  AUTO_FIX                        — "false" to only comment and never push
"""
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com"
REPO = os.environ.get("REPO", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
AUTO_FIX = os.environ.get("AUTO_FIX", "true").lower() != "false"

# (name, base_url, env_var, model_fallbacks) — first entry with a key wins.
# Each provider tries its models in order; 404/410/EOL advances to the next
# (NIM retired meta/llama-3.3-70b-instruct on 2026-08-26 — lesson learned).
PROVIDERS = [
    ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions",
     "NVIDIA_API_KEY", ("meta/llama-4-maverick-17b-128e-instruct",
                        "meta/llama-4-scout-17b-16e-instruct",
                        "meta/llama-3.3-70b-instruct")),
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
     "GEMINI_API_KEY", ("gemini-2.5-flash", "gemini-2.0-flash")),
    ("groq", "https://api.groq.com/openai/v1/chat/completions",
     "GROQ_API_KEY", ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")),
    ("openrouter", "https://openrouter.ai/api/v1/chat/completions",
     "OPENROUTER_API_KEY", ("meta-llama/llama-3.3-70b-instruct:free",
                            "deepseek/deepseek-chat-v3-0324:free")),
    ("huggingface", "https://router.huggingface.co/v1/chat/completions",
     "HF_TOKEN", ("meta-llama/Llama-3.3-70B-Instruct",
                  "Qwen/Qwen2.5-72B-Instruct")),
]

SCHEMA_HINT = (
    'Return a JSON object {"findings":[...]} with 3 to 6 findings. NEVER return an empty list. '
    'Each element: '
    '{"path": <file path as in the diff>, "line": <new-file line number>, '
    '"severity": "critical"|"warning"|"suggestion", '
    '"comment": <string with the EXACT GitHub suggestion block shown below, and NOTHING else>}. '
    'The "comment" string MUST be formatted EXACTLY like this, with no extra prose and no labels: '
    '```suggestion\\n<REPLACEMENT CODE FOR THAT ONE LINE ONLY>\\n```\\n'
    'Rules: (1) the first line is literally ```suggestion and the block ends with ``` on its own line; '
    '(2) put ONLY the replacement code inside the fence; '
    '(3) if you want to explain why, put ONE short sentence AFTER the closing ```; '
    '(4) NEVER use a ```python or ```yaml fence; NEVER prefix with [SUGGESTION]/[WARNING] labels; '
    '(5) the replacement must be a real, compilable fix for that exact diff line. '
    'Prefer real, verifiable issues: hardcoded org names, dead/no-op code, wrong API usage, '
    'missing error handling, quoting/heredoc bugs, unused variables. '
    'Line numbers MUST match added/changed lines present in the diff. Do not invent paths or lines.'
)


# --------------------------------------------------------------------------
# GitHub API helpers
# --------------------------------------------------------------------------
def github(path, method="GET", data=None):
    url = GITHUB_API + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get_diff():
    """Whole-PR unified diff, falling back to the paginated files API when the
    diff media type is rejected (GitHub caps it at 300 files)."""
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3.diff")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        if e.code != 406:
            raise
    # Fallback: synthesize a unified diff from per-file patches (no file cap).
    files = []
    page = 1
    while True:
        data = github(f"/repos/{REPO}/pulls/{PR_NUMBER}/files?per_page=100&page={page}")
        files.extend(data)
        if len(data) < 100:
            break
        page += 1
    return "\n".join(
        f"diff --git a/{f['filename']} b/{f['filename']}\n+++ b/{f['filename']}\n{f.get('patch', '')}"
        for f in files if f.get("patch")
    )


# --------------------------------------------------------------------------
# Diff parsing -> (path, new_file_line) for every added/context line
# --------------------------------------------------------------------------
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


def parse_diff(diff_text):
    """Return {path: [(new_line, content)]} for added/context lines we can comment on."""
    files = {}
    path = None
    new_line = 0
    for raw in diff_text.splitlines():
        m = FILE_RE.match(raw)
        if m:
            path = m.group(1)
            files.setdefault(path, [])
            continue
        h = HUNK_RE.match(raw)
        if h:
            new_line = int(h.group(3))
            continue
        if raw.startswith("+++") and "/dev/null" in raw:
            # deletion-only file: there are no new-file lines to comment on
            path = None
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            # removed line does not exist in the new file; skip it
            pass
        else:
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
    return files


# --------------------------------------------------------------------------
# LLM call (free endpoints only)
# --------------------------------------------------------------------------
def resolve_provider():
    """Return (name, url, key, models) for the first configured provider."""
    base_override = os.environ.get("LLM_BASE_URL")
    model_override = os.environ.get("LLM_MODEL")
    for name, url, env_var, models in PROVIDERS:
        key = os.environ.get(env_var)
        if env_var == "NVIDIA_API_KEY" and not key:
            key = os.environ.get("VIBE_API_KEY")  # legacy alias
        if key:
            ordered = (model_override,) + tuple(m for m in models if m != model_override) if model_override else models
            return name, base_override or url, key, ordered
    return None, None, None, (model_override,) if model_override else ("gemini-2.5-flash",)


def call_llm(diff_text, pr_title, pr_body):
    name, url, key, models = resolve_provider()
    if not key:
        raise RuntimeError(
            "No free-tier LLM key configured. Add one of: "
            + ", ".join(p[2] for p in PROVIDERS)
        )
    system = (
        "You are Sovereign-ULA's automated code-review agent. Produce inline, commit-ready fixes. "
        "Output strict JSON of per-line suggestions using GitHub ```suggestion syntax."
    )
    user = f"PR: {pr_title}\n\nDescription:\n{pr_body or '(none)'}\n\nDIFF:\n{diff_text[:16000]}\n\n{SCHEMA_HINT}"
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    last_err = None
    for provider_name, p_url, p_key, p_models in [p for p in PROVIDERS if os.environ.get(p[2])]:
        u = os.environ.get("LLM_BASE_URL") if provider_name == name else p_url
        for model in p_models:
            body = dict(payload, model=model)
            req = urllib.request.Request(u, method="POST")
            req.add_header("Authorization", f"Bearer {p_key}")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "sovereign-ai-reviewer")
            for _ in range(2):
                try:
                    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=240) as r:
                        resp = json.loads(r.read().decode())
                    content = resp["choices"][0]["message"]["content"].strip()
                    if content.startswith("```"):
                        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S)
                    data = json.loads(content)
                    print(f"LLM provider used: {provider_name} ({model})")
                    return data.get("findings", data) if isinstance(data, dict) else data
                except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
                    last_err = e
                    print(f"LLM call failed on {provider_name}/{model}: {e}; retrying...")
            # model-level EOL/404/410 failures fall through to the next model
    raise last_err or RuntimeError("all LLM providers failed")


# --------------------------------------------------------------------------
# Apply a suggestion to a real file (agentic fix)
# --------------------------------------------------------------------------
def extract_replacement(comment):
    """Pull the code out of a ```suggestion fence; return list of lines (no fence)."""
    m = re.search(r"```suggestion\n(.*?)\n```", comment, flags=re.S)
    if not m:
        m = re.search(r"```suggestion\s*(.*?)\s*```", comment, flags=re.S)
    if not m:
        return None
    return m.group(1).split("\n")


def apply_fix(path, line, replacement_lines):
    if not os.path.exists(path):
        return False, f"path not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    idx = line - 1
    if idx < 0 or idx >= len(lines):
        return False, f"line {line} out of range (file has {len(lines)} lines)"
    lines[idx:idx + 1] = replacement_lines
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True, f"patched {path}:{line}"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    if not REPO or not PR_NUMBER:
        print("REPO and PR_NUMBER environment variables must be set.")
        return
    if not any(os.environ.get(p[2]) for p in PROVIDERS):
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": "## AI Agent Review\n\n⚠️ No free-tier LLM key provided "
                        "(NVIDIA_API_KEY / GEMINI_API_KEY / GROQ_API_KEY / "
                        "OPENROUTER_API_KEY / HF_TOKEN); AI review could not run."})
        print("No LLM key; posted notice.")
        return

    pr = github(f"/repos/{REPO}/pulls/{PR_NUMBER}")
    diff = get_diff()
    print(f"Fetched diff ({len(diff)} chars) for PR #{PR_NUMBER}")
    diff_lines = parse_diff(diff)

    try:
        findings = call_llm(diff, pr.get("title", ""), pr.get("body", ""))
    except Exception as e:
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": f"## AI Agent Review\n\nReview agent error: `{e}`. No review posted."})
        print(f"LLM error: {e}")
        return

    if not isinstance(findings, list):
        findings = []

    applied = []
    skipped = []
    for f in findings:
        path = f.get("path")
        line = int(f.get("line", 0))
        sev = f.get("severity", "suggestion")
        body = (f.get("comment") or "").strip()
        if not path or line <= 0 or not body:
            continue
        repl = extract_replacement(body)
        if not repl:
            skipped.append(f"{path}:{line} (no suggestion block)")
            continue
        if AUTO_FIX and sev in ("critical", "warning"):
            ok, msg = apply_fix(path, line, repl)
            if ok:
                applied.append(f"{path}:{line} [{sev}]")
            else:
                skipped.append(f"{path}:{line} ({msg})")
        else:
            skipped.append(f"{path}:{line} [{sev}] comment-only")

    summary_lines = ["## 🤖 AI Agent Review (Sovereign-Ula)", ""]
    if applied:
        head_ref = pr["head"]["ref"]
        try:
            subprocess.run(["git", "config", "user.email", "agent@sovereign-ula"], check=True)
            subprocess.run(["git", "config", "user.name", "sovereign-ai-reviewer"], check=True)
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m",
                            "fix: apply AI review suggestions (auto)\n\nAgentic PR review: committed inline fixes from the free-endpoint LLM reviewer."],
                           check=True)
            subprocess.run(["git", "push", "origin", f"HEAD:{head_ref}"], check=True)
            summary_lines.append(f"**Auto-fixed {len(applied)} issue(s)** (pushed to `{head_ref}`):")
            for a in applied:
                summary_lines.append(f"- ✅ {a}")
        except subprocess.CalledProcessError as e:
            summary_lines.append(f"⚠️ Applied {len(applied)} fix(es) locally but push failed: `{e}`.")
            for a in applied:
                summary_lines.append(f"- ✅ {a}")
    if skipped:
        summary_lines.append("")
        summary_lines.append(f"Comment-only / skipped ({len(skipped)}):")
        for s in skipped[:8]:
            summary_lines.append(f"- ⏭️ {s}")
    if not applied and not skipped:
        summary_lines.append("No actionable inline issues found. Diff looks clean.")

    summary_lines.append("")
    summary_lines.append("*Automated agentic LLM review runner (free endpoints only).*")
    github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST", {"body": "\n".join(summary_lines)})
    print(f"Posted summary. applied={len(applied)} skipped={len(skipped)}")
    if applied:
        print(f"SOVEREIGN_RESULT=APPLIED={len(applied)}")
    else:
        print("SOVEREIGN_RESULT=NOFIX")


if __name__ == "__main__":
    main()
