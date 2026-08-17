#!/usr/bin/env python3
"""
Sovereign ULA — AI Agent PR Review Runner (agentic: reviews AND fixes).
"""
import os
import sys
import json
import re
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
        if raw.startswith("+++") and "/dev/null" in raw:
            path = None
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            # removed line, ignore for "new file line" mapping
            continue
        else:
            files.setdefault(path, []).append((new_line, raw[1:]))
            new_line += 1
    return files

# LLM schema hint
SCHEMA_HINT = (
    'Return a JSON object {"findings":[...]} with 3 to 6 findings. NEVER return an empty list. '
    'Each element: '
    '{"path": <file path as in the diff>, "line": <new-file line number>, '
    '"severity": "critical"|"warning"|"suggestion", '
    '"comment": <string with the EXACT GitHub suggestion block shown below, and NOTHING else>}. '
    'The "comment" string MUST be formatted EXACTLY like this, with no extra prose and no labels: '
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
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    req = urllib.request.Request(LLM_BASE_URL, method="POST")
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
