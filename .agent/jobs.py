"""Hermes persistent job engine — grok-bot style: work, test, verify,
repair, and keep going NONSTOP until the job's verify suite is green.

A job is a real improvement goal with its own verify commands (e.g. "add a
test and run pytest until it passes"). GitHub Actions caps each pulse at
~22 minutes, so a hard job may span several 30-minute pulses:

  pulse N   execute the job's commands once, run verify_commands
            if failing -> LLM REPAIR loop (bounded per pulse)
            still failing -> leave status=running with full error context
  pulse N+1 resume exactly there: re-verify, repair again, ...
  ...        until verify_commands are green -> repo-wide gate -> status=done
            (the change is committed and opens a draft PR)

Escapes (never burn tokens forever):
  - per-pulse repair budget (default 3 LLM repairs)
  - total-pulse cap (default 6) -> status=blocked with last errors
  - no LLM key -> blocked immediately when a repair is needed

Safety (mirrors runner.py):
  - destructive commands are filtered by the caller's is_dangerous()
  - repairs never touch .agent/, secret-ish paths (.env/keys/keystores)
  - every written file passes refactor's per-file syntax gate; failures are
    skipped (never silently overwrite with broken content)
  - no remote-payload self-mutation: the model edits THIS repo's files and
    runs only explicit, filtered shell commands
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import nim_client  # noqa: E402
import refactor  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

PULSE_REPAIR_BUDGET = 3
MAX_PULSES = 6
MAX_COMMANDS_PER_PULSE = 5

FILE_BLOCK_RE = re.compile(r"<<<FILE:\s*([^\n>]+?)>>>\n(.*?)<<<END>>>", re.DOTALL)
RUN_BLOCK_RE = re.compile(r"<<<RUN>>>\n(.*?)<<<END>>>", re.DOTALL)

SECRET_PATH_HINTS = (
    ".env", "keystore", ".jks", ".p12", "/keys/", "/secrets/",
    "credentials", "signing", "roboshadow",
)


def _log(ctx, msg: str) -> None:
    ctx["log"](msg)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (slug or "job")[:60]


# --------------------------------------------------------------------------
# Job lifecycle helpers
# --------------------------------------------------------------------------

def new_job(plan: dict, state: dict) -> dict:
    """Instantiate a persistent job from a planner plan that carries
    verify_commands (the planner decides an item needs real test-until-green
    work instead of a one-shot edit)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title = plan.get("title", "untitled improvement")
    job = {
        "slug": slugify(title),
        "title": title,
        "description": plan.get("description", ""),
        "commands": plan.get("commands", [])[:MAX_COMMANDS_PER_PULSE],
        "expected_files": plan.get("expected_files", []),
        "verify_commands": plan.get("verify_commands", []),
        "status": "running",
        "executed": False,
        "pulses": 0,
        "repairs_used": 0,
        "pulse_budget": PULSE_REPAIR_BUDGET,
        "max_pulses": MAX_PULSES,
        "command_results": [],
        "last_errors": [],
        "created": now,
        "updated": now,
    }
    state.setdefault("jobs", {})[job["slug"]] = job
    return job


def pick_active(state: dict):
    """Oldest running job (created first)."""
    jobs = state.get("jobs", {})
    running = [(k, v) for k, v in jobs.items() if v.get("status") in ("running", "queued")]
    if not running:
        return None
    running.sort(key=lambda kv: kv[1].get("created", ""))
    return running[0]


def prune(state: dict, keep: int = 12) -> None:
    """Keep the jobs map small: drop oldest done/blocked beyond `keep`."""
    jobs = state.get("jobs", {})
    if len(jobs) <= keep:
        return
    terminal = sorted(
        ((k, v) for k, v in jobs.items() if v.get("status") in ("done", "blocked")),
        key=lambda kv: kv[1].get("updated", ""),
    )
    for k, _ in terminal[: max(0, len(jobs) - keep)]:
        del jobs[k]


# --------------------------------------------------------------------------
# Command / verify execution (through caller-provided ctx)
# --------------------------------------------------------------------------

def _execute(ctx, commands: list) -> list:
    results = []
    for cmd in (commands or [])[:MAX_COMMANDS_PER_PULSE]:
        if ctx["is_dangerous"](cmd):
            _log(ctx, f"⛔ job command blocked by safety filter: {cmd}")
            results.append({"command": cmd, "blocked": True})
            continue
        rc, out = ctx["sh"](cmd, timeout=300)
        results.append({"command": cmd, "rc": rc, "output": out})
        if rc != 0:
            break
    return results


def _verify_suite(ctx, commands: list) -> list:
    """Run a job's verify commands. Returns a list of failure texts ([] = green)."""
    failures = []
    for cmd in (commands or []):
        _log(ctx, f"  ✅ verify: $ {cmd}")
        rc, out = ctx["sh"](cmd, timeout=600)
        if rc != 0:
            failures.append(f"$ {cmd}\nexit={rc}\n{out[:3000]}")
    return failures


# --------------------------------------------------------------------------
# Repair loop
# --------------------------------------------------------------------------

REPAIR_SYSTEM = """You are the Surgeon inside Hermes, an autonomous maintainer for the
sovereign-ula repository (a rebranded UserLAnd Android app, package
dev.soveriegn.ula; Kotlin app + shell/Python tooling + GitHub Actions workflows +
a Linux bootstrap under bootstrap/, universal layer in bootstrap/core/).

A job's VERIFY SUITE is failing. Fix it with the SMALLEST possible correct
changes. Do not rewrite working files, do not refactor, do not change the
architecture, do not fix unrelated things.

You may first run an exploratory command:
<<<RUN>>>
<single safe shell command>
<<<END>>>

Then output ONLY the files that need changes, COMPLETE files (not diffs):
<<<FILE: relative/path/to/file>>>
<complete corrected file contents>
<<<END>>>

RULES:
- Never touch .agent/, .env files, keys, keystores, or anything secret.
- Never suggest destructive/network/force-push commands.
- If the verify failure is environmental (network, missing tool) rather than a
  code defect, output only: NOOP
"""


def _is_secret_path(rel: str) -> bool:
    lowered = rel.lower()
    return any(hint in lowered for hint in SECRET_PATH_HINTS)


def _repair_once(ctx, job: dict, failures: list):
    """One LLM repair iteration. Returns (changed_anything, new_failures)."""
    if not nim_client.available():
        _log(ctx, "⚠ no NVIDIA_API_KEY — repair loop cannot run")
        return False, failures
    _log(ctx, f"🔧 asking NIM for a surgical repair ({len(failures)} failure(s))...")
    user = json.dumps({
        "job_title": job.get("title"),
        "job_description": job.get("description"),
        "verify_commands": job.get("verify_commands"),
        "expected_files": job.get("expected_files"),
        "failures": failures[-5:],
    }, indent=1)
    try:
        raw = nim_client.complete(REPAIR_SYSTEM, user, timeout=420)
    except Exception as err:  # noqa: BLE001
        _log(ctx, f"⚠ repair LLM call failed: {err}")
        return False, failures

    if "NOOP" in raw.strip().upper()[:12]:
        _log(ctx, "  repair says NOOP (environmental failure?)")
        return False, failures

    for cmd in RUN_BLOCK_RE.findall(raw):
        _log(ctx, f"  exploratory: $ {cmd.strip()[:120]}")
        _execute(ctx, [cmd.strip()])

    changed = False
    for match in FILE_BLOCK_RE.finditer(raw):
        rel = match.group(1).strip().lstrip("/")
        body = match.group(2).strip("\n") + "\n"
        if rel.startswith(".agent/") or _is_secret_path(rel):
            _log(ctx, f"  ⛔ refused to repair {rel} (protected path)")
            continue
        if not refactor._syntax_ok(rel, body):
            _log(ctx, f"  ✗ {rel} failed the syntax gate — not written")
            continue
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        _log(ctx, f"  🔧 patched {rel} ({len(body)} chars)")
        changed = True

    new_failures = _verify_suite(ctx, job.get("verify_commands", []))
    return changed, new_failures


# --------------------------------------------------------------------------
# One pulse of a job
# --------------------------------------------------------------------------

def advance(ctx, job: dict):
    """Drive one 30-min pulse of a job. Mutates job in place; returns the job.

    End states per pulse: done (verify green + repo gate green) | blocked
    (cap hit or no LLM for repair) | running (needs another pulse)."""
    job["pulses"] = int(job.get("pulses", 0)) + 1
    job["repairs_used"] = 0
    job["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _log(ctx, f"⏳ job pulse {job['pulses']}/{job.get('max_pulses')}: {job['title']}")

    if not job.get("executed"):
        _log(ctx, "  ▶ executing job commands")
        job["command_results"] = _execute(ctx, job.get("commands", []))
        job["executed"] = True
    job.setdefault("command_results", [])

    verify_cmds = job.get("verify_commands") or []
    failures = _verify_suite(ctx, verify_cmds)

    budget = int(job.get("pulse_budget", PULSE_REPAIR_BUDGET))
    while failures and int(job["repairs_used"]) < budget:
        if not nim_client.available():
            job["last_errors"] = failures[-6:]
            job["status"] = "blocked"
            job["blocked_reason"] = "verify failing and no NVIDIA_API_KEY for repairs"
            _log(ctx, f"⛔ job blocked: {job['blocked_reason']}")
            return job
        _, failures = _repair_once(ctx, job, failures)
        job["repairs_used"] = int(job["repairs_used"]) + 1

    if not failures:
        # Job's own suite is green — run the repo-wide gate as final safety.
        gate = ctx["repo_gate"]()
        if not gate:
            job["status"] = "done"
            job["last_errors"] = []
            _log(ctx, f"🎉 job DONE: {job['title']} (pulse {job['pulses']})")
            return job
        failures = [f"{g.get('file')}: {g.get('message')}" for g in gate]

    # Still failing after this pulse's budget.
    job["last_errors"] = failures[-6:]
    if int(job["pulses"]) >= int(job.get("max_pulses", MAX_PULSES)):
        job["status"] = "blocked"
        job["blocked_reason"] = f"still failing after {job['pulses']} pulses"
        _log(ctx, f"⛔ job blocked: {job['blocked_reason']}")
    else:
        job["status"] = "running"
        _log(ctx, f"↻ job still running — resumes next pulse with {len(failures)} failure(s)")
    return job
