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
    return files


# --------------------------------------------------------------------------
# LLM call: strict JSON schema of inline findings
# --------------------------------------------------------------------------
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
        return

    if not isinstance(findings, list):
        findings = []
    post_review(findings, diff_lines)


if __name__ == "__main__":
    main()
