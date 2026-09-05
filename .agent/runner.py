#!/usr/bin/env python3
"""Hermes Autonomous Runner — continuous 30-minute improve loop for sovereign-ula.

Scheduled by .github/workflows/autonomous-agent.yml (cron */30). Each cycle:

  SYNC     -> fetch latest, work on a dedicated `hermes-autonomous` branch
  ANALYZE  -> static checks: FSM layout, shell/python syntax, secret scan, TODO scan
  REFACTOR -> deterministic LLM fix engine (refactor.py): syntax-gated full-file
              rewrites of the top-scored fixable findings (full / fix-only modes)
  JOBS     -> persistent verify-until-green jobs (jobs.py): resume any running
              job and repair until its verify suite is green; plans that carry
              verify_commands become jobs and run nonstop across pulses
  PLAN     -> NIM LLM picks ONE structural improvement (analysis + backlog)
  EXECUTE  -> apply the plan via guarded shell commands
  VERIFY   -> re-run static checks; revert on failure (never ship broken code)
  LEARN    -> append run record to the knowledge base (.agent/history.jsonl ->
              SQLite mirror + trend stats), persist state.json
  SHIP     -> commit state + code changes, push the branch, open/update a
              DRAFT PR only when code actually changed (never main)
  REPORT   -> markdown report -> .agent/logs/ + best-effort Google Drive backup

Safety (non-negotiable):
  - never pushes to main; everything lands as a draft PR on hermes-autonomous
  - destructive commands are blocked by a filter
  - hardcoded-secret findings become issues, never auto-fixed
  - if verification fails after a change, the change is reverted
  - state persists in .agent/state.json + history.jsonl (committed to the
    branch) so the backlog and trends survive ephemeral Actions workspaces

Modes: full (default) | analyze-only | fix-only.
"""
import argparse
import ast
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_sync  # noqa: E402
import jobs  # noqa: E402
import knowledge  # noqa: E402
import nim_client  # noqa: E402
import refactor  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGENT = Path(__file__).resolve().parent
STATE_PATH = AGENT / "state.json"
LOGS_DIR = AGENT / "logs"
BRANCH = "hermes-autonomous"
MAX_AUTOFIX_PER_RUN = 5

DANGEROUS = (
    "rm -rf /",
    "mkfs",
    "dd if=",
    "> /dev/sd",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "git push origin master",
    "git push origin main",
    "git push -f",
    "git reset --hard",
    "history -c",
)
BANNED_DISTRO_FILES = ("extractFilesystem.sh", "addNonRootUser.sh", "termuxvoid-shim.sh", "busybox", "tvrun")
DISTRO_DIRS = ("ubuntu", "arch", "alpine", "debian", "fedora")
SECRET_PATTERNS = (
    r"nvapi-[A-Za-z0-9_\-]{16,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY",
)


def log(msg: str) -> None:
    print(f"[hermes] {msg}", flush=True)


def sh(cmd: str, cwd=None, timeout: int = 180):
    """Run a shell command, capture output, truncate huge results."""
    log(f"$ {cmd}")
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd or ROOT), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"
    out = (proc.stdout or "") + ("\n[stderr]\n" + proc.stderr if proc.stderr else "")
    out = out.strip()
    if len(out) > 12000:
        out = out[:6000] + "\n...[truncated]...\n" + out[-4000:]
    return proc.returncode, out or "(no output)"


def git(*args: str, cwd=None, timeout: int = 120) -> str:
    rc, out = sh("git " + " ".join(shlex.quote(a) for a in args), cwd=cwd, timeout=timeout)
    return out.strip()


def is_dangerous(cmd: str) -> bool:
    return any(p in cmd for p in DANGEROUS)


def default_branch() -> str:
    out = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if out.startswith("origin/"):
        return out.replace("origin/", "")
    rc, ls = sh("git ls-remote --symref origin HEAD", timeout=60)
    m = re.search(r"ref: refs/heads/(\S+)\s+HEAD", ls or "")
    return m.group(1) if m else "master"


# --------------------------------------------------------------------------
# State — persisted across cron runs via the branch
# --------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            log("⚠ corrupt state.json — starting fresh")
    return {"backlog": [], "completed": [], "trends": {}, "runs": 0, "last_run": None, "jobs": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1))


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def fsm_violations() -> list:
    """Mirror of the hermes_fsm_enforce.yml preflight: agnostic assets must
    live in bootstrap/core/, never inside a distro dir."""
    findings = []
    for distro in DISTRO_DIRS:
        distro_dir = ROOT / "bootstrap" / distro
        if not distro_dir.exists():
            continue
        for f in sorted(distro_dir.rglob("*")):
            if f.is_file() and f.name in BANNED_DISTRO_FILES:
                findings.append({
                    "type": "fsm",
                    "severity": "HIGH",
                    "file": str(f.relative_to(ROOT)),
                    "message": f"FSM violation: '{f.name}' must live in bootstrap/core/, not bootstrap/{distro}/",
                })
    return findings


def syntax_findings() -> list:
    findings = []
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.parts:
            continue
        rel = str(f.relative_to(ROOT))
        if f.suffix == ".sh":
            rc, out = sh(f"bash -n {shlex.quote(rel)}", timeout=60)
            if rc != 0:
                findings.append({"type": "syntax", "severity": "HIGH", "file": rel, "message": out})
        elif f.suffix == ".py":
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as err:
                findings.append({
                    "type": "syntax", "severity": "HIGH", "file": rel,
                    "message": f"{err.__class__.__name__}: {err}",
                })
    return findings


def secret_findings() -> list:
    """Scan tracked files for hardcoded secrets. These are NEVER auto-fixed."""
    rc, out = sh("git ls-files")
    findings = []
    for rel in out.splitlines():
        f = ROOT / rel
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            for m in re.finditer(pattern, text):
                line_no = text[: m.start()].count("\n") + 1
                findings.append({
                    "type": "secret",
                    "severity": "CRITICAL",
                    "file": rel,
                    "line": line_no,
                    "message": f"possible hardcoded secret ({pattern.split('[')[0]}...)",
                })
    return findings


def analyze() -> dict:
    log("🔍 analyzing repository...")
    findings = fsm_violations() + syntax_findings()
    secrets = secret_findings()
    todo_scan = []
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.parts:
            continue
        rel = str(f.relative_to(ROOT))
        if rel.startswith(".agent/"):
            continue
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(r"\b(TODO|FIXME|HACK)\b", line):
                    todo_scan.append({"type": "todo", "file": rel, "line": i, "message": line.strip()[:120]})
                    break  # one entry per file keeps the prompt small
        except OSError:
            continue

    status = git("status", "--short")
    head = git("rev-parse", "--short", "HEAD")
    return {
        "head": head,
        "working_tree_changes": status,
        "findings": findings[:50],
        "secrets": secrets[:20],
        "todos": todo_scan[:30],
        "file_count": sum(1 for f in ROOT.rglob("*") if f.is_file() and ".git" not in f.parts),
    }


# --------------------------------------------------------------------------
# LLM planning
# --------------------------------------------------------------------------

PLAN_SYSTEM = """You are the Lead SWE for the sovereign-ula repository: a rebranded
UserLAnd Android app (package dev.soveriegn.ula) with an Ubuntu Noble proot
bootstrap under bootstrap/ (universal support layer in bootstrap/core/, distro
config in bootstrap/<distro>/). Your goal is total repo perfection through
SMALL, safe, verifiable improvements — one per cycle.

Choose the SINGLE most impactful improvement for this 30-minute cycle from the
analysis findings and the backlog. Prefer, in order:
1. FSM or CI issues (fixes that make a failing check pass)
2. repo hygiene / docs drift (README, PLANS, RULES must stay truthful)
3. small safe code fixes (never large rewrites, never refactors)
4. backlog items tagged HIGH priority

RULES:
- Never modify secrets, keystores, or .env-like files.
- Never suggest commands that rewrite git history, force-push, or touch main.
- Never edit files under .agent/ (the runner owns that space).
- Every command must be safe to run non-interactively in a fresh checkout.
- Keep expected_files to the files you actually change.

Output ONLY valid JSON (no markdown fences), schema:
{
  "title": "short PR title",
  "description": "2-3 sentence rationale, referencing specific findings",
  "commands": ["single shell command", ...],   // max 3
  "expected_files": ["path/to/file", ...],
  "verify_commands": ["real check command", ...],  // OPTIONAL: supply ONLY
      // when this improvement must be TESTED until green (e.g. add a test
      // script and run it to prove the fix). Omit for one-shot edits; the
      // runner applies one-shot plans immediately and reverts on failure.
  "next_run_goal": "one line for the backlog"
}
If no improvement is worth making this cycle, output {"noop": true, "reason": "..."}."""


def plan(analysis: dict, state: dict):
    if not nim_client.available():
        log("⚠ NVIDIA_API_KEY not set — skipping LLM planning (static analysis only)")
        return None
    log("🧠 asking NIM for the single best improvement...")
    user = json.dumps({"analysis": analysis, "backlog": state.get("backlog", [])[:20]}, indent=1)
    raw = nim_client.complete(PLAN_SYSTEM, user)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            log("⚠ LLM returned non-JSON plan; treating as noop")
            return {"noop": True, "reason": raw[:200]}
        parsed = json.loads(raw[start : end + 1])
    return parsed


# --------------------------------------------------------------------------
# Execute / verify / ship
# --------------------------------------------------------------------------

def execute(plan: dict) -> list:
    results = []
    for cmd in plan.get("commands", [])[:MAX_AUTOFIX_PER_RUN]:
        if is_dangerous(cmd):
            log(f"⛔ blocked dangerous command: {cmd}")
            results.append({"command": cmd, "blocked": True})
            continue
        rc, out = sh(cmd, timeout=300)
        results.append({"command": cmd, "rc": rc, "output": out})
        if rc != 0:
            break
    return results


def verify() -> list:
    log("✅ verifying (syntax + FSM)...")
    failures = syntax_findings() + fsm_violations()
    return [f for f in failures if f["severity"] == "HIGH"]


def revert(expected_files: list) -> None:
    """Undo a change that failed verification — never ship broken code."""
    for rel in expected_files:
        if rel.startswith(".agent/"):
            continue
        git("checkout", "--", rel)
    log("↩ reverted failing changes")


def changed_files() -> list:
    """Working-tree changes vs HEAD, excluding the runner's own durable .agent
    state (state.json/history.jsonl are committed by ship() regardless). Used
    to know what the planner actually changed when it omits expected_files."""
    paths = set(git("diff", "--name-only").splitlines())
    rc, out = sh("git ls-files --others --exclude-standard", timeout=60)
    paths |= {p.strip() for p in out.splitlines()}
    return sorted(p for p in paths if p and not p.startswith(".agent/"))


def open_draft_pr(title: str, body: str) -> None:
    if not os.environ.get("GH_TOKEN"):
        log("⚠ GH_TOKEN not set — skipping draft PR")
        return
    head = BRANCH
    rc, out = sh(
        f"gh pr list --head {shlex.quote(head)} --state open --json number",
        timeout=60,
    )
    existing = out.strip() if rc == 0 else ""
    if existing and existing != "[]":
        try:
            pr_number = json.loads(existing)[0]["number"]
        except (json.JSONDecodeError, IndexError):
            pr_number = None
        if pr_number:
            rc, out = sh(
                f"gh pr edit {pr_number} --title {shlex.quote(title)} --body {shlex.quote(body)}",
                timeout=120,
            )
            log(f"✏️ updated draft PR #{pr_number}" if rc == 0 else f"⚠ PR edit failed: {out}")
            return
    rc, out = sh(
        "gh pr create --draft "
        f"--base {shlex.quote(default_branch())} "
        f"--head {shlex.quote(head)} "
        f"--title {shlex.quote(title)} "
        f"--body {shlex.quote(body)}",
        timeout=120,
    )
    log(out if rc == 0 else f"⚠ PR create failed: {out}")


def ship(state: dict, applied: list, plan: dict | None, wip: bool = False) -> None:
    """Commit state + any code changes, push the branch, and open/update a
    draft PR only when code actually changed this cycle.

    state.json / history.jsonl are committed on every run (even noops) so the
    backlog and knowledge log survive between ephemeral Actions workspaces;
    the PR is reserved for real changes to avoid noise. WIP runs (a persistent
    job mid-flight) commit with an honest work-in-progress message."""
    plan = plan or {}
    if applied:
        title = plan.get("title") or f"Hermes: {len(applied)} automated fix(es)"
        summary = "\n".join(f"- {a.get('file') or a.get('note') or a.get('status')}" for a in applied)
        body = (
            f"🤖 **Hermes autonomous run**\n\n"
            f"{plan.get('description', 'Automated fixes from the refactor engine.')}\n\n"
            f"{summary}\n\n_Automated draft — review before merging._\n\n"
            f"Backlog: {json.dumps(state.get('backlog', [])[-5:])}"
        )
    elif wip:
        title = f"Hermes: WIP — {plan.get('title') or 'job in progress'}"
        body = (
            f"🤖 **Hermes autonomous run** — work in progress on: "
            f"**{plan.get('title') or 'job'}**\n\n{plan.get('description', '')}\n\n"
            f"_Not ready to merge — the verify-until-green job is still running and "
            f"auto-continues on the next 30-minute cycle._"
        )
    else:
        title = "Hermes: state sync (no code changes)"
        body = (
            "🤖 **Hermes autonomous run** — analysis recorded, no code changes "
            "this cycle.\n\n_Automated draft — review before merging._"
        )

    rc, out = sh("git add -A", timeout=120)
    if rc != 0:
        log(f"⚠ git add failed: {out}")
        return
    staged = git("diff", "--cached", "--name-only").splitlines()
    if not staged:
        log("nothing to commit")
        return
    commit_msg = "hermes: " + (plan.get("title") or title)
    rc, out = sh(f"git commit -m {shlex.quote(commit_msg)}", timeout=120)
    if rc != 0 and "nothing to commit" not in out:
        log(f"⚠ commit failed: {out}")
        return
    rc, out = sh(f"git push -u origin {shlex.quote(BRANCH)}", timeout=180)
    log(out)
    if rc == 0 and applied:
        open_draft_pr(title, body)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Hermes autonomous repo-improvement runner")
    ap.add_argument("--mode", choices=["full", "analyze-only", "fix-only"], default="full")
    args = ap.parse_args()

    log(f"starting cycle (mode={args.mode})")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # SYNC: work on the persistent hermes-autonomous branch, merging latest default.
    git("fetch", "origin", "--quiet")
    default = default_branch()
    rc, _ = sh(
        f"git checkout -B {BRANCH} origin/{shlex.quote(BRANCH)} 2>/dev/null "
        f"|| git checkout -B {BRANCH} origin/{shlex.quote(default)}"
    )
    if rc != 0:
        log("⚠ could not prepare branch; continuing on current checkout")
    rc, out = sh(f"git merge origin/{shlex.quote(default)} --no-edit -m 'sync: hermes-autonomous <- latest default branch'")
    if rc != 0:
        log(f"⚠ merge conflict: {out[:300]}")
        sh("git merge --abort")

    state = load_state()
    state["runs"] = state.get("runs", 0) + 1
    state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    analysis = analyze()
    for s in analysis.get("secrets", []):
        log(f"🔒 SECRET at {s['file']}:{s.get('line', '?')} — will NOT be auto-fixed")

    refactor_results: list = []
    outcomes: list = []        # {"file", "status": applied|reverted, "note"}
    verify_failures: list = []
    plan_result: dict | None = None
    results: list = []

    # 1) REFACTOR: deterministic, syntax-gated LLM fixes (full / fix-only).
    if args.mode in ("full", "fix-only"):
        refactor_results = refactor.engine_run(analysis.get("findings", []))
        for r in refactor_results:
            ffile = r.get("file") or r.get("finding", {}).get("file", "?")
            log(f"🔧 refactor {r['status']}: {ffile} — {r.get('message', '')}")
        applied_files = [r["file"] for r in refactor_results if r.get("status") == "applied"]
        if applied_files:
            verify_failures = verify()
            if verify_failures:
                revert(applied_files)
                outcomes += [{"file": f, "status": "reverted", "note": "post-refactor verify failed"}
                             for f in applied_files]
            else:
                log(f"🔧 {len(applied_files)} file(s) fixed and verified")
                outcomes += [{"file": f, "status": "applied", "note": "refactor engine"} for f in applied_files]
                analysis = analyze()  # refresh so the planner/report see the fixed tree

    # 2) JOBS / PLAN:
    #    - a running verify-until-green job is resumed and driven as far as
    #      this pulse's repair budget allows — nonstop across pulses until
    #      done or blocked.
    #    - otherwise the LLM planner picks ONE improvement. Plans carrying
    #      verify_commands are instantiated as persistent jobs (work that must
    #      be tested until green); everything else is one-shot.
    job_ctx = {"sh": sh, "is_dangerous": is_dangerous, "repo_gate": verify, "log": log}
    running_job = None       # job driven this cycle (for the report)
    blocked_job = False
    if args.mode in ("full", "fix-only"):
        active = jobs.pick_active(state)
        if active:
            job = active[1]
            running_job = job
            log(f"⏳ resuming job '{job.get('slug')}' — pulse {job.get('pulses', 0) + 1}")
            jobs.advance(job_ctx, job)
            results = job.get("command_results", [])
            plan_result = {"title": job.get("title"), "description": job.get("description")}
            if job.get("status") == "done":
                changed = job.get("expected_files") or changed_files()
                if changed:
                    outcomes += [{"file": f, "status": "applied", "note": job.get("title")}
                                 for f in changed]
                log(f"🎉 job complete after {job.get('pulses')} pulses: {job.get('title')}")
            elif job.get("status") == "blocked":
                blocked_job = True
                plan_result["_wip"] = True
                outcomes.append({"file": f"(job {job.get('slug')})", "status": "blocked",
                                 "note": job.get("blocked_reason", "blocked")})
                log(f"⛔ job blocked: {job.get('blocked_reason')}")
            else:
                plan_result["_wip"] = True
                log(f"↻ job still running — {len(job.get('last_errors', []))} failure(s); resumes next cycle")
        elif args.mode == "full":
            if verify_failures:
                plan_result = {"noop": True, "reason": "skipped: refactor changes failed verification"}
            else:
                plan_result = plan(analysis, state)
            if plan_result and not plan_result.get("noop"):
                if plan_result.get("verify_commands"):
                    # Persistent job: work/test/repair until green, across pulses.
                    job = jobs.new_job(plan_result, state)
                    running_job = job
                    plan_result["_wip"] = True
                    save_state(state)  # crash-safe before driving
                    log(f"📦 new persistent job: {job.get('slug')}")
                    jobs.advance(job_ctx, job)
                    results = job.get("command_results", [])
                    if job.get("status") == "done":
                        changed = job.get("expected_files") or changed_files()
                        if changed:
                            outcomes += [{"file": f, "status": "applied", "note": job.get("title")}
                                         for f in changed]
                        log(f"🎉 job complete in one pulse: {job.get('title')}")
                    elif job.get("status") == "blocked":
                        blocked_job = True
                        outcomes.append({"file": f"(job {job.get('slug')})", "status": "blocked",
                                         "note": job.get("blocked_reason", "blocked")})
                        log(f"⛔ job blocked: {job.get('blocked_reason')}")
                    else:
                        log(f"↻ job running — resumes next cycle ({len(job.get('last_errors', []))} failures)")
                else:
                    expected = plan_result.get("expected_files", [])
                    results = execute(plan_result)
                    vf = verify()
                    if vf:
                        verify_failures = vf
                        revert(expected)
                        outcomes += [{"file": f, "status": "reverted", "note": plan_result.get("title", "planner change")}
                                     for f in expected]
                    elif results and all(r.get("rc") == 0 for r in results):
                        log(f"🛠️ plan applied: {plan_result.get('title')}")
                        # Trust expected_files when the planner listed them;
                        # otherwise derive what actually changed so the change
                        # still gets a PR.
                        changed = plan_result.get("expected_files") or changed_files()
                        if not changed:
                            changed = ["(repo changes)"]
                        outcomes += [
                            {"file": f, "status": "applied",
                             "note": plan_result.get("title", "planner change")}
                            for f in changed
                        ]
                    else:
                        log("⚠ plan commands did not all succeed — no change claimed")
        else:  # fix-only and no active job
            plan_result = {"noop": True, "reason": "fix-only: refactor engine only"}
    else:  # analyze-only
        plan_result = {"noop": True, "reason": "analyze-only mode"}
    if plan_result is None:
        plan_result = {"noop": True, "reason": "LLM unavailable (NVIDIA_API_KEY not set)"}

    # 3) LEARN: record outcomes, backlog, durable knowledge + state.
    applied = [o for o in outcomes if o["status"] == "applied"]
    if outcomes:
        state.setdefault("completed", []).append(
            {"run": state["runs"], "ts": state["last_run"], "outcomes": outcomes}
        )
        state["completed"] = state["completed"][-50:]
    next_goal = plan_result.get("next_run_goal")
    if next_goal:
        state.setdefault("backlog", []).append(next_goal)
    state["backlog"] = state.get("backlog", [])[-25:]
    save_state(state)

    knowledge.append_run({
        "run_id": run_id,
        "ts": state["last_run"],
        "head": analysis.get("head"),
        "mode": args.mode,
        "findings": analysis.get("findings", [])[:50],
        "secrets_count": len(analysis.get("secrets", [])),
        "applied": [o["file"] for o in applied],
        "backlog": state.get("backlog", []),
    })
    trends = knowledge.get_trends()
    state["trends"] = trends
    jobs.prune(state)
    save_state(state)
    log(f"📈 knowledge: {trends.get('total_runs', 0)} runs, trend={trends.get('trend', 'stable')}")

    # 4) SHIP: commit state (+code) to the branch every run for durability;
    # a draft PR is opened/updated only when code actually changed. WIP jobs
    # commit mid-flight progress so the next pulse resumes exactly where this
    # one stopped (nonstop until the job's verify suite is green).
    ship(state, applied, plan_result, wip=bool(plan_result.get("_wip")))

    # 5) REPORT: log file + Drive backup.
    report = drive_sync.compose_report(
        args.mode, analysis, plan_result, results, state, verify_failures,
        refactor_results=refactor_results, trends=trends, job=running_job,
    )
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    log_path = LOGS_DIR / f"report-{ts}.md"
    log_path.write_text(report)
    log(f"report: {log_path}")
    drive_sync.upload_report(report, f"hermes-report-{ts}.md")

    if blocked_job:
        log("cycle finished: a job was blocked (see report)")
        return 1
    if verify_failures:
        log("cycle finished WITH verification failures (changes reverted)")
        return 1
    log("cycle finished clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
