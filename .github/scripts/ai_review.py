#!/usr/bin/env python3
"""
Sovereign ULA — AI Agent PR Review Runner ("gitapp-type" LLM calling).

STANDALONE AI reviewer that posts INLINE, commit-ready suggestions via the
GitHub **Pull Request Review API** (not a plain comment dump). Output uses
GitHub's ```suggestion markdown so each finding is a one-click "Apply" fix
mapped to a real diff line — like an integrated review app.

Flow:
  1. Fetch the PR diff (raw patch) + metadata.
  2. Parse the patch into per-file hunks, tracking new-file line numbers so
     inline comments land on the correct line.
  3. Send the diff to an LLM (NVIDIA / OpenAI-compatible) with a STRICT schema:
     return a JSON array of {path, line, severity, comment} where `comment`
     embeds a ```suggestion ... ``` block with the replacement code.
  4. POST a Pull Request Review (event COMMENT, or REQUEST_CHANGES if any
     critical) carrying the inline comments. If the model finds nothing
     actionable, post one short summary comment instead.

Secrets (repo Settings -> Secrets and variables -> Actions):
  GITHUB_TOKEN   auto-provided by Actions
  NVIDIA_API_KEY (or VIBE_API_KEY) — LLM bearer token
  LLM_BASE_URL   optional chat-completions endpoint override
  LLM_MODEL      optional model override (default: meta/llama-3.3-70b-instruct)
Sovereign ULA — AI Agent PR Review Runner (agentic: reviews AND fixes).
"""
import os
import sys
import json
import re
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"
REPO = os.environ["REPO"]
PR_NUMBER = os.environ["PR_NUMBER"]
TOKEN = os.environ["GITHUB_TOKEN"]

LLM_BASE_URL = os.environ.get("LLM_BASE_URL") or "https://integrate.api.nvidia.com/v1/chat/completions"
LLM_MODEL = os.environ.get("LLM_MODEL") or "nvidia/llama-3.1-nemotron-70b-instruct"  # NVIDIA NIM; strong code reviewer
# Fallback if the above is unavailable: "meta/llama-3.3-70b-instruct"
LLM_KEY = os.environ.get("NVIDIA_API_KEY") or os.environ.get("VIBE_API_KEY")


# --------------------------------------------------------------------------
# GitHub API helper
# --------------------------------------------------------------------------
def github(path, method="GET", data=None):
    url = GITHUB_API + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    body = json.dumps(data).encode() if data is not None else None
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=body, timeout=120) as r:
        return json.loads(r.read().decode())


def get_diff():
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
import subprocess
import urllib.request
import urllib.error
import time

GITHUB_API = "https://api.github.com"
REPO = os.environ.get("REPO", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
AUTO_FIX = os.environ.get("AUTO_FIX", "true").lower() != "false"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL") or "https://integrate.api.nvidia.com/v1/chat/completions"
# Multi-provider key resolution (pick first present)
LLM_KEY = (
    os.environ.get("NVIDIA_API_KEY")
    or os.environ.get("VIBE_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GROQ_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("TOGETHER_API_KEY")
)
# Model fallback chain (first non-empty will be probed)
LLM_MODEL_CHAIN = [m for m in [
    os.environ.get("LLM_MODEL"),
    "deepseek-ai/deepseek-v4-pro",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-large",
] if m]

LLM_MODEL = None

def resolve_llm_model():
    """Probe the chain with a tiny ping; pick the first that answers."""
    global LLM_MODEL
    if not LLM_MODEL_CHAIN:
        LLM_MODEL = "deepseek-ai/deepseek-v4-pro"
        print("::warning::No model candidates available; using hardcoded fallback.")
        return LLM_MODEL
    for candidate in LLM_MODEL_CHAIN:
        try:
            payload = json.dumps({
                "model": candidate,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }).encode()
            req = urllib.request.Request(LLM_BASE_URL, data=payload, method="POST")
            if LLM_KEY:
                req.add_header("Authorization", f"Bearer {LLM_KEY}")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "sovereign-ai-reviewer")
            with urllib.request.urlopen(req, timeout=15) as r:
                if 200 <= getattr(r, "status", 200) < 300:
                    LLM_MODEL = candidate
                    print(f"LLM model resolved: {candidate}")
                    return candidate
        except Exception as err:
            print(f"model unavailable, trying next: {candidate} ({err})")
            continue
    LLM_MODEL = LLM_MODEL_CHAIN[0] if LLM_MODEL_CHAIN else "deepseek-ai/deepseek-v4-pro"
    print("::warning::No model in the fallback chain responded; using first entry.")
    return LLM_MODEL

# ---------------- GitHub helpers ----------------
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
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3.diff")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


# --------------------------------------------------------------------------
# Diff parsing -> (path, new_file_line) for every added/context line
# --------------------------------------------------------------------------
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


def parse_diff(diff_text):
    """Return {path: [(new_line, content)]} for added/context lines we can comment on."""
# Diff parsing
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")

def parse_diff(diff_text):
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
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("diff "):
            # '--- a/...' and '+++ b/...' (or /dev/null) — only the b/ one sets path;
            # ignore /dev/null (deletion-only) so we don't key on None.
            if raw.startswith("+++") and "/dev/null" in raw:
                path = None
        if raw.startswith("+++") and "/dev/null" in raw:
            path = None
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            # added line -> commentable on its new-file line
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            pass  # deleted line, no new-file position
        else:
            # context line -> also commentable
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            # removed line, ignore for "new file line" mapping
            continue
        else:
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
    return files


# --------------------------------------------------------------------------
# LLM call: strict JSON schema of inline findings
# --------------------------------------------------------------------------
# LLM schema hint
SCHEMA_HINT = (
    'Return a JSON object {"findings":[...]} with 3 to 6 findings. NEVER return an empty list. '
    'Each element: '
    '{"path": <file path as in the diff>, "line": <new-file line number>, '
    '"severity": "critical"|"warning"|"suggestion", '
    '"comment": <string with the EXACT GitHub suggestion block shown below, and NOTHING else>}. '
    'The "comment" string MUST be formatted EXACTLY like this, with no extra prose and no labels: '
    '```suggestion\\n<REPLACEMENT CODE FOR THAT ONE LINE ONLY>\\n```\\n'
    'Rules: (1) the first line is literally ```suggestion and the block ends with ``` on its own line; '
    '(2) put ONLY the replacement code inside the fence — no explanation inside it; '
    '(3) if you want to explain why, put ONE short sentence AFTER the closing ```; '
    '(4) NEVER use a ```python or ```yaml or other language-tagged fence; NEVER prefix with [SUGGESTION] or [WARNING] labels; '
    '(5) the replacement must be a real, compilable one-line (or few-line) fix for that exact diff line. '
    'Prefer real, verifiable issues: hardcoded org names, dead/no-op code, wrong API usage, '
    'missing error handling, quoting/heredoc bugs, unused variables. '
    'Line numbers MUST match added/changed lines present in the diff. Do not invent paths or lines.'
)


def call_llm(diff_text, pr_title, pr_body):
    system = (
        "You are Sovereign-ULA's automated code-review agent for an Android app "
        "(a UserLAnd fork, applicationId dev.soveriegn.ula) and its Linux distro "
        "bootstrap shell scripts. You produce INLINE, commit-ready fixes. "
        "You never write summaries or 'Looks Good' walls. You output strict JSON "
        "of per-line suggestions using GitHub ```suggestion syntax (literal ```suggestion fence, "
        "NOT ```python/```yaml, and NO [SUGGESTION]/[WARNING] labels). "
        "You are precise: real line numbers, real file paths, real fixes. "
        "No hallucinated boilerplate. No generic security lectures. "
        "You ALWAYS return findings (3-6); you never return an empty list."
    )
    user = (
        f"PR: {pr_title}\n\nDescription:\n{pr_body or '(none)'}\n\n"
        f"DIFF:\n{diff_text[:16000]}\n\n{SCHEMA_HINT}"
    )
    '```suggestion\n<REPLACEMENT CODE FOR THAT ONE LINE ONLY>\n```\n'
)

def call_llm(diff_text, pr_title, pr_body):
    system = (
        "You are Sovereign-ULA's automated code-review agent. Produce inline, commit-ready fixes. "
        "Output strict JSON of per-line suggestions using GitHub ```suggestion syntax."
    )
    user = f"PR: {pr_title}\n\nDescription:\n{pr_body or '(none)'}\n\nDIFF:\n{diff_text[:16000]}\n\n{SCHEMA_HINT}"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    req = urllib.request.Request(LLM_BASE_URL, method="POST")
    req.add_header("Authorization", f"Bearer {LLM_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    last_err = None
    for attempt in range(2):  # one retry on transient timeout
    if LLM_KEY:
        req.add_header("Authorization", f"Bearer {LLM_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    last_err = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, data=json.dumps(payload).encode(), timeout=240) as r:
                resp = json.loads(r.read().decode())
            break
        except OSError as e:  # socket.timeout / URLError both subclass OSError
            last_err = e
            print(f"LLM call attempt {attempt+1} failed: {e}; retrying...")
    else:
        raise last_err
    content = resp["choices"][0]["message"]["content"].strip()
    # The model may wrap JSON in fences despite instructions; unwrap.
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S)
    data = json.loads(content)
    # Accept either {"findings": [...]} or a bare array.
    return data.get("findings", data) if isinstance(data, dict) else data


# --------------------------------------------------------------------------
# Post a Pull Request Review with inline comments
# --------------------------------------------------------------------------
def post_review(findings, diff_lines):
    """findings: list of dicts. diff_lines: parsed diff for validation."""
    comments = []
    has_critical = False
    for f in findings:
        path = f.get("path")
        line = int(f.get("line", 0))
        sev = f.get("severity", "suggestion")
        body = f.get("comment", "").strip()
        if not path or line <= 0 or not body:
            continue
        # Validate the line exists in the parsed diff for that file.
        valid_lines = {ln for ln, _ in diff_lines.get(path, [])}
        if line not in valid_lines:
            # Nudge to nearest valid line to avoid a 422 from GitHub.
            cand = [l for l in valid_lines if l >= line]
            if cand:
                line = min(cand)
            else:
                continue
        if sev == "critical":
            has_critical = True
        comments.append({
            "path": path,
            "line": line,
            "side": "RIGHT",
            "body": f"**[{sev.upper()}]** {body}",
        })
    if not comments:
        notice = (
            "## 🤖 AI Agent Review (Sovereign-Ula)\n\n"
            f"_Model: `{LLM_MODEL}`_\n\n"
            "No actionable inline issues found. Diff looks clean.\n\n"
            "---\n*Automated LLM review runner (inline suggestions).*"
        )
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST", {"body": notice})
        print("Posted clean summary (no inline comments).")
        return
    event = "REQUEST_CHANGES" if has_critical else "COMMENT"
    head = github(f"/repos/{REPO}/pulls/{PR_NUMBER}")["head"]["sha"]
    payload = {
        "commit_id": head,
        "event": event,
        "body": f"## 🤖 AI Agent Review (Sovereign-Ula)\n_Model: `{LLM_MODEL}`_\n"
                f"{len(comments)} inline suggestion(s). Apply each with the "
                f"one-click button. {'Requesting changes on critical items.' if has_critical else ''}",
        "comments": comments,
    }
    github(f"/repos/{REPO}/pulls/{PR_NUMBER}/reviews", "POST", payload)
    print(f"Posted PR review ({event}) with {len(comments)} inline comment(s).")


# --------------------------------------------------------------------------
def main():
    if not LLM_KEY:
        notice = (
            "## AI Agent Review\n\n"
            "⚠️ No `NVIDIA_API_KEY` / `VIBE_API_KEY` secret configured; AI review "
            "could not run. Add it in repo Settings → Secrets and variables → Actions."
        )
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST", {"body": notice})
        print("No LLM key; posted notice.")
        return

        except OSError as e:
            last_err = e
            print(f"LLM call failed: {e}; retrying...")
            time.sleep(1)
    else:
        raise last_err
    # Accept different response shapes: aim to extract content
    content = ""
    if isinstance(resp, dict):
        # OpenAI-ish
        choices = resp.get("choices")
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        else:
            content = json.dumps(resp)
    else:
        content = str(resp)
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S)
    try:
        data = json.loads(content)
    except Exception:
        # as last resort try to parse the whole response as JSON
        data = resp
    findings = None
    if isinstance(data, dict) and "findings" in data:
        findings = data["findings"]
    elif isinstance(data, list):
        findings = data
    else:
        findings = []
    return findings

def extract_replacement(comment):
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

def main():
    if not REPO or not PR_NUMBER:
        print("REPO and PR_NUMBER environment variables must be set.")
        return
    if not LLM_KEY:
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": "## AI Agent Review\n\n⚠️ No LLM API key provided; AI review could not run."})
        print("No LLM key; posted notice.")
        return

    resolve_llm_model()

    pr = github(f"/repos/{REPO}/pulls/{PR_NUMBER}")
    diff = get_diff()
    print(f"Fetched diff ({len(diff)} chars) for PR #{PR_NUMBER}")
    diff_lines = parse_diff(diff)

    try:
        findings = call_llm(diff, pr.get("title", ""), pr.get("body", ""))
    except Exception as e:  # never hard-fail CI on a review hiccup
        print(f"LLM/review error: {e}")
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": f"## AI Agent Review\n\nReview agent error: `{e}`. No review posted."})
    except Exception as e:
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": f"## AI Agent Review\n\nReview agent error: `{e}`. No review posted."})
        print(f"LLM error: {e}")
        return

    if not isinstance(findings, list):
        findings = []
    post_review(findings, diff_lines)


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

    summary_lines = [f"## 🤖 AI Agent Review (Sovereign-Ula)", f"_Model: `{LLM_MODEL}`_", ""]
    if applied:
        head_ref = pr["head"]["ref"]
        try:
            subprocess.run(["git", "config", "user.email", "agent@sovereign-ula"], check=True)
            subprocess.run(["git", "config", "user.name", "sovereign-ai-reviewer"], check=True)
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m",
                            "fix: apply AI review suggestions (auto)\n\nAgentic PR review: committed inline fixes from the LLM reviewer."],
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
    summary_lines.append("*Automated agentic LLM review runner.*")
    github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST", {"body": "\n".join(summary_lines)})
    print(f"Posted summary. applied={len(applied)} skipped={len(skipped)}")
    if applied:
        print(f"SOVEREIGN_RESULT=APPLIED={len(applied)}")
    else:
        print("SOVEREIGN_RESULT=NOFIX")

if __name__ == "__main__":
    main()
