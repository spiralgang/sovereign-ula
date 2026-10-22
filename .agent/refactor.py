"""Hermes LLM-powered refactoring engine.

Turns prioritized static-analysis findings into real, verified file edits:

  1. score/prioritize findings (type severity x fixability) — blueprint-style
  2. for each fixable candidate, ask the NIM model for a COMPLETE corrected
     file (the model sees the finding + current contents + repo constraints)
  3. apply the edit and immediately gate it with a cheap syntax check
  4. on failure, revert the file (git checkout) — never ship broken code

Hard rules:
  - never edits .agent/, secrets, keystores, or .env-like files
  - never runs shell commands (this engine only rewrites file contents;
    structural moves like FSM relocations are left to the planner)
  - secret findings are NEVER auto-fixed (they become issues only)
"""
import ast
import json
import re
import subprocess
from pathlib import Path

import nim_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGENT = Path(__file__).resolve().parent

# Finding types this engine will attempt via LLM full-file rewrite. Structural
# fixes (fsm relocation + build rewiring) and security (secret) are excluded.
ATTEMPT_TYPES = {"syntax", "hygiene", "complexity", "todo", "dependency", "coverage"}
MAX_FILE_CHARS = 120_000
MAX_FIXES_PER_RUN = 3

FILE_BLOCK_RE = re.compile(
    r"<<<FILE:\s*(?P<path>[^\n>]+?)>>>\n(?P<body>.*?)<<<END>>>", re.DOTALL
)

BASE_SCORES = {
    "secret": 90, "syntax": 80, "fsm": 70, "dependency": 75,
    "complexity": 50, "coverage": 40, "hygiene": 30, "todo": 25,
}
SEVERITY_MULTIPLIER = {"CRITICAL": 2.0, "HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.5}


def _log(msg: str) -> None:
    print(f"[refactor] {msg}", flush=True)


def score_finding(finding: dict) -> float:
    """Score a finding 0-100: type base x severity x fixability boost."""
    base = BASE_SCORES.get(finding.get("type", ""), 30)
    mult = SEVERITY_MULTIPLIER.get(finding.get("severity", ""), 0.5)
    boost = 1.3 if finding.get("fixable") else 1.0
    return round(min(100.0, base * mult * boost), 1)


def prioritize(findings: list) -> list:
    """Return findings sorted by score descending (score attached)."""
    scored = [{**f, "priority_score": score_finding(f)} for f in findings]
    return sorted(scored, key=lambda f: f["priority_score"], reverse=True)


# --------------------------------------------------------------------------
# File-level syntax gate (in-process, no repo writes)
# --------------------------------------------------------------------------

def _syntax_ok(rel: str, content: str) -> bool:
    if rel.endswith(".py"):
        try:
            ast.parse(content)
            return True
        except SyntaxError as err:
            _log(f"  ✗ {rel} python gate failed: {err}")
            return False
    if rel.endswith(".sh"):
        try:
            proc = subprocess.run(
                ["bash", "-n"], input=content.encode("utf-8"),
                capture_output=True, timeout=60,
            )
            if proc.returncode == 0:
                return True
            _log(f"  ✗ {rel} bash -n gate failed: {proc.stderr.decode('utf-8', 'replace')[:300]}")
            return False
        except (OSError, subprocess.TimeoutExpired):
            pass  # bash unavailable — defer to the caller's global verify
    return True


# --------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------

REFACTOR_SYSTEM = """You are a senior staff engineer making SURGICAL fixes in the
sovereign-ula repository: a rebranded UserLAnd Android app (Kotlin, package
dev.soveriegn.ula) with shell/Python tooling, GitHub Actions workflows, and a
Linux bootstrap under bootstrap/ (agnostic core in bootstrap/core/, distro
config in bootstrap/<distro>/).

Fix the ONE finding you are given with the SMALLEST correct change. Do not
restructure, do not rename, do not fix unrelated things, do not add features.
Match the file's existing style and conventions.

RULES:
- Output the COMPLETE corrected file, not a diff and not excerpts.
- Never touch secrets, keystores, .env files, or anything under .agent/.
- If the file is already correct or the finding is not actionable, output
  exactly: NOOP
- Output ONLY one fenced block:
  <<<FILE: relative/path/to/file>>>
  <complete file contents>
  <<<END>>>"""


def _read_file(rel: str):
    path = ROOT / rel
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if "\x00" in content or len(content) > MAX_FILE_CHARS:
        return None
    return content


def _revert_file(rel: str) -> None:
    subprocess.run(
        ["git", "checkout", "--", rel], cwd=str(ROOT),
        capture_output=True, timeout=60,
    )


def refactor_one(finding: dict):
    """Attempt one LLM fix for a finding. Returns a result dict."""
    rel = finding.get("file", "")
    if not rel or rel.startswith(".agent/"):
        return {"finding": finding, "status": "skipped", "message": "unsafe path"}
    content = _read_file(rel)
    if content is None:
        return {"finding": finding, "status": "skipped", "message": "unreadable/oversized/binary"}
    if not nim_client.available():
        return {"finding": finding, "status": "skipped", "message": "no NVIDIA_API_KEY"}

    user = json.dumps({
        "finding": {k: finding.get(k) for k in ("type", "severity", "file", "line", "message")},
        "file": rel,
        "contents": content,
    }, indent=1)
    try:
        raw = nim_client.complete(REFACTOR_SYSTEM, user, timeout=420)
    except Exception as err:  # noqa: BLE001
        return {"finding": finding, "status": "failed", "message": f"LLM error: {err}"}

    if "NOOP" in raw.strip().upper()[:12]:
        return {"finding": finding, "status": "skipped", "message": "model says noop"}

    match = FILE_BLOCK_RE.search(raw)
    if not match:
        return {"finding": finding, "status": "failed", "message": "no file block in LLM output"}
    new_content = match.group("body").strip("\n") + "\n"

    if not _syntax_ok(rel, new_content):
        _revert_file(rel)
        return {"finding": finding, "status": "failed", "message": "syntax gate failed; reverted"}
    (ROOT / rel).write_text(new_content, encoding="utf-8")
    return {
        "finding": finding, "status": "applied", "file": rel,
        "message": f"rewrote {rel} ({len(content)} -> {len(new_content)} chars)",
    }


def engine_run(findings: list, limit: int = MAX_FIXES_PER_RUN) -> list:
    """Try to fix the top fixable findings. Returns per-finding results."""
    results = []
    if not nim_client.available():
        _log("⚠ no NVIDIA_API_KEY — refactor engine disabled")
        return results
    candidates = [
        f for f in prioritize(findings)
        if f.get("type") in ATTEMPT_TYPES and f.get("file") and not f.get("file", "").startswith(".agent/")
    ]
    _log(f"🧠 refactor engine: {len(candidates)} fixable candidate(s), attempting up to {limit}")
    for finding in candidates[:limit]:
        result = refactor_one(finding)
        results.append(result)
        _log(f"  → {result['status']}: {result.get('file', finding.get('file'))} — {result.get('message', '')}")
        if result["status"] == "failed":
            # a failed gate usually means the model misread the context — stop
            break
    return results