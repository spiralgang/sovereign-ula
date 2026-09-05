# Hermes Autonomous Runner — Architecture

A continuous repository-improvement agent for `spiralgang/sovereign-ula`,
scheduled every 30 minutes by GitHub Actions. It is modeled on the
GitHub-copilot-coding-agent / SWE-agent pattern: **plan → edit → verify →
draft PR**, run on a loop, with durable knowledge across runs.

The layer mapping below is the reference for anyone extending the system —
each layer is one module with one job.

## Layer map

| Blueprint layer         | Where it lives                          | Responsibility                                                      |
|-------------------------|-----------------------------------------|---------------------------------------------------------------------|
| Orchestration           | `.github/workflows/autonomous-agent.yml`| Cron pulse (`*/30`), run modes, concurrency guard, secrets wiring   |
| State machine / cycle   | `.agent/runner.py` (`main()`)           | SYNC → ANALYZE → REFACTOR → JOBS → PLAN → EXECUTE → VERIFY → LEARN → SHIP |
| Persistent jobs         | `.agent/jobs.py`                        | verify-until-green engine: repair loop, resume across pulses, caps   |
| Analysis engine         | `.agent/runner.py` (`analyze()`)        | FSM-layout preflight, shell/Python syntax, secret scan, TODO scan   |
| Prioritization          | `.agent/refactor.py` (`score/prioritize`)| Findings scored type × severity × fixability (0–100)               |
| Action engine (fixes)   | `.agent/refactor.py` (`engine_run`)     | LLM full-file surgical rewrites, per-file syntax gate, revert on fail|
| Action engine (structural) | `.agent/runner.py` (`plan`/`execute`) | NIM LLM picks ONE structural improvement, applied via guarded shell  |
| Verification           | `.agent/runner.py` (`verify()`/`revert()`)| Re-runs syntax + FSM gates; any failure reverts the change          |
| PR verifier matrix     | `.github/workflows/agent-verifier-matrix.yml` | Matrix of independent checks on every Hermes draft PR          |
| Knowledge store        | `.agent/knowledge.py` + `state.json`    | Cross-run log (`history.jsonl`, committed) → SQLite mirror + trends  |
| Report / Drive sync    | `.agent/drive_sync.py`                  | Markdown report → `.agent/logs/` → Google Drive (best-effort)       |
| LLM client             | `.agent/nim_client.py`                  | NVIDIA NIM (reasoning) or Google GenAI free tier, stream=true logs    |

## One 30-minute cycle

1. **SYNC** — fetch origin; `git checkout -B hermes-autonomous` off the
   latest default branch (`master`), merging it in. All agent work happens on
   this dedicated branch; the default branch is never touched by the runner.
2. **ANALYZE** — static picture of the repo: FSM violations (agnostic assets
   must live in `bootstrap/core/`, never a distro dir), shell/Python syntax
   errors, hardcoded secrets (CRITICAL, never auto-fixed), TODO/FIXME scan.
3. **REFACTOR** (`full` + `fix-only`) — `refactor.py` scores the findings,
   and for the top fixable candidates asks the NIM model for a COMPLETE
   corrected file, gates it with an in-process syntax check, writes it, then
   `verify()`s the whole tree. Any failure → `git checkout` revert.
4. **JOBS** (`full` + `fix-only`) — if a persistent job is running, it is
   resumed and driven to the end of this pulse’s repair budget (work → test →
   repair, nonstop across pulses until green or blocked). New plans that
   carry `verify_commands` are instantiated as jobs.
5. **PLAN** (`full` only, when no job is running) — the LLM receives the
   fresh analysis + backlog and returns JSON: `{title, description,
   commands[≤3], expected_files, verify_commands?, next_run_goal}`.
   `verify_commands` turns the plan into a persistent job; otherwise it is
   one-shot: commands execute through a destructive-command filter,
   verification gates the result, failures are reverted.
6. **LEARN** — a run record (findings, secrets count, applied files, backlog)
   is appended to `.agent/history.jsonl` (committed to the branch → survives
   ephemeral Actions runners, capped + pruned), mirrored into SQLite
   (`knowledge.db`, regenerated each run, gitignored), and trend stats
   (`total_runs`, avg findings, trend direction) are stored in `state.json`.
7. **SHIP** — `git add -A` (repo-wide — refactor/planner/job edits are NOT
   limited to `.agent/`), commit, `git push -u origin hermes-autonomous`. A
   **draft PR** is created (or updated) **only when code actually changed** —
   noop cycles just sync state; mid-flight jobs commit as honest **WIP** so
   the next pulse resumes exactly where this one stopped. Never pushes to the
   default branch.
8. **REPORT** — `drive_sync.compose_report()` renders one markdown report
   (including the job’s status + last failures) that lands in `.agent/logs/`
   (uploaded as an Actions artifact too) and is backed up to Google Drive
   when configured.

Exit code is 1 when a cycle finished with verification failures (reverted)
or a job was blocked, so the Actions run is visibly red.

## Run modes (`workflow_dispatch` or the cron default)

| Mode          | Refactor engine | LLM planner | Branch commit + PR      |
|---------------|-----------------|-------------|-------------------------|
| `full`        | ✅              | ✅          | ✅ (PR only if changed) |
| `fix-only`    | ✅              | —           | ✅ (PR only if changed) |
| `analyze-only`| —               | —           | report only             |

A `full` cycle that finds a running job drives the job and skips the planner
that pulse; `fix-only` drives jobs + the refactor engine and never plans.
WIP job cycles push to the branch but never open a PR until the job is done.

## Persistent jobs — work until done (nonstop)

The job engine (`jobs.py`) is what makes the runner behave like a grok-style
bot that keeps working, testing, and verifying until the job is complete —
rather than giving up after one attempt. A job is created when the planner
returns `verify_commands` (real checks the change must pass, e.g. “add a test
and run it”), and lives in `state.json` → `jobs`:

```jsonc
{
  "slug": "fix-thing", "title": "...", "description": "...",
  "commands": ["..."], "expected_files": ["..."],
  "verify_commands": ["pytest -q ..."],
  "status": "running",        // running | done | blocked
  "executed": false, "pulses": 0, "repairs_used": 0,
  "pulse_budget": 3, "max_pulses": 6,
  "command_results": [], "last_errors": [], "created": "...", "updated": "..."
}
```

Each pulse:

1. execute the job’s commands **once** (guarded by the destructive filter),
2. run `verify_commands` — green? then the repo-wide gate runs as final
   safety and the job is **done** (change ships as a draft PR),
3. failing? the **repair loop** asks the NIM model for surgical file fixes
   (REPAIR protocol), re-verifies, up to `pulse_budget` repairs,
4. still failing when the pulse budget runs out → `status=running` with the
   last errors persisted; the next 30-minute pulse resumes exactly there
   (mid-flight code is committed as WIP on the agent branch).

Escapes (never burn tokens forever): per-pulse repair budget (3), total-pulse
cap (6 ≈ 3 hours → `blocked` with reason), and immediate `blocked` when a
repair is needed but no `NVIDIA_API_KEY` is set. Repairs are further gated:
no `.agent/`, no `.env`/keystore/secret paths, and every file rewrite must
pass the per-file syntax gate.

## PR verifier matrix (the external test-and-verify gate)

`agent-verifier-matrix.yml` fans one job into a **matrix of independent
verifiers** (defined by the `define-verifiers` job output via `fromJSON`) on
every Hermes draft PR head (`hermes-autonomous` / `hermes/*`):

| Axis      | Check                                                            |
|-----------|------------------------------------------------------------------|
| `fsm`     | no agnostic assets (shim/support/busybox…) inside distro dirs    |
| `shell`   | `bash -n` over every tracked `*.sh`                              |
| `python`  | `py_compile` over every tracked `*.py`                           |
| `yaml`    | every `.github/workflows/*.yml` parses                           |
| `secrets` | no hardcoded NVIDIA/GitHub/AWS keys or private-key material      |

The cells run in parallel (`fail-fast: false`), so a broken PR shows exactly
which axis failed. This is the “matrix” half of the design: the agent works,
and CI independently tests + verifies — a PR can never sit green-badged while
its checks are red. Manual run: `gh workflow run agent-verifier-matrix.yml`.

## Knowledge store format

- `state.json` — committed durable state: `runs`, `last_run`, `backlog`
  (≤25), `completed` (≤50 outcome records), `trends`.
- `history.jsonl` — committed durable log: one JSON line per run with the
  full findings snapshot. Pruned to the last ~300 records past 600.
- `knowledge.db` — SQLite mirror (`runs`/`findings`/`future_work`) rebuilt
  from `history.jsonl` on every run; **gitignored** (binary, regenerable).
- `.agent/.gitignore` — excludes `knowledge.db`, `logs/`, `__pycache__/` so
  the branch only carries small text state.

## Google Drive backup — setup (optional, ~5 minutes)

The Drive upload is best-effort: with no credentials the runner simply skips
it (reports still live in `.agent/logs/` + the Actions artifact). To enable:

1. **Create a service account** at console.cloud.google.com → IAM & Admin →
   Service Accounts (or reuse one from another project).
2. **Enable the Google Drive API** for that project (APIs & Services →
   Enable APIs → “Google Drive API”).
3. **Create a JSON key** for the account (Keys → Add Key → JSON). Locally:
   ```bash
   base64 -w0 path/to/sa-key.json     # copy the output
   ```
4. **Set repo secrets** (Settings → Secrets and variables → Actions):
   - `GDRIVE_CREDENTIALS` — the base64 string from step 3 (required)
   - `GDRIVE_FOLDER_ID` — id from a Drive folder URL (`.../folders/<ID>`),
     optional: when unset the agent find-or-creates a folder named
     `hermes-run-reports` under the service account’s own Drive root
   - `GDRIVE_FOLDER_NAME` — optional override for that folder name
5. **Share** (only if you use a folder owned by a real account): share the
   folder with the service account’s email (`…@….iam.gserviceaccount.com`) as
   Editor, or uploads will 403.
6. Trigger once with `workflow_dispatch` (mode `analyze-only`) and confirm
   the log line `✓ report backed up to Drive`.

The service account needs no other Google permissions; Drive scope is
`https://www.googleapis.com/auth/drive`.

## Secrets required by the workflow

| Secret              | Required | Used for                                  |
|---------------------|----------|-------------------------------------------|
| `NVIDIA_API_KEY`    | either   | NIM reasoning model (planner + refactor)  |
| `GEMINI_API_KEY`    | either   | Google GenAI free tier (AI Studio key)    |
| `GENAI_MODEL`       | optional | GenAI model override (default gemini-2.5-flash) |
| `LLM_PROVIDER`      | optional | `nvidia` / `gemini` force (else auto)     |
| `GDRIVE_CREDENTIALS`| optional | Drive backup (base64 service-account JSON)|
| `GDRIVE_FOLDER_ID`  | optional | Drive destination folder                   |
| `GITHUB_TOKEN`      | auto     | gh CLI: branch push, draft PRs            |

Either `NVIDIA_API_KEY` or `GEMINI_API_KEY` is required for LLM-driven cycles
(without either, the runner degrades to static analysis + reports). The
workflow dispatch lets you pick the provider per run; cron runs auto (NVIDIA
wins when both are set).

## In-distro agentic-coder layer

Independent of the repo-side runners, every distro rootfs built by
`bootstrap/<distro>/input/main.sh` bakes an open agent environment via
`bootstrap/core/agent-tooling/install-agent-tools.sh` (universal layer → FSM
correct; opt out with `SOVEREIGN_SKIP_AGENT_TOOLS=1`):

- **Antigravity CLI (`agy`)** — Google's agent-first terminal coding agent,
  successor to the decommissioned Gemini CLI (retired 2026-06-18). Official
  installer → `~/.local/bin/agy`; auth on first run.
- **uv + `/opt/agents` venv** — Astral uv manages the python toolchain; the
  `google-genai` free-tier SDK (streaming) is installed into the managed venv.
- **Node 22 (NodeSource)** — “server-hosted” node manager: apt's Node 18 is
  below the MCP engines floor (>= 20.18.1); the apt repo + docker rootfs
  layer cache make the upgrade free and lag-managed.
- **MCP plugins** — `filesystem`, `github`, `context7` servers installed
  GLOBALLY at build time (zero npx cold-start per agent launch) and wired in
  `~/.gemini/config/mcp_config.json` (`mcpServers`, Antigravity schema);
  templates + docs shipped to `/support/agent-tooling/` inside the rootfs.
- **profile wiring** — `/etc/profile.d/sovereign-agents.sh` (agy PATH, uv
  venv, ready hint); keys/tokens are never baked into the image (auth on
  first `agy` run, or env at runtime).

On the repo side, both the Hermes runner and the verifier matrix install
python deps with **uv** (`astral-sh/setup-uv` → `uv pip install` / `uvx`) —
never bare pip.

Proprietary agent UIs (aria-termux, freebuff platform, Antigravity desktop, …)
are not installable packages — their open, installable cores are the tools
above (`agy` = Antigravity's CLI core) plus this repo's own `hermes-agent`
(clone the repo in-env; the same runner code powers the GitHub Actions side).

## Hard safety rules (non-negotiable)

- The default branch is never written to by the agent: everything lands on
  `hermes-autonomous` as a **draft** PR requiring human review. Branch
  protection / required reviews on the default branch are the backstop.
- Destructive-command filter (`DANGEROUS` in `runner.py`): `rm -rf /`, mkfs,
  dd to block devices, force-push, `git reset --hard`, history wipe, etc.
- Secrets are detected and *reported as issues only* — never auto-fixed, and
  the refactor engine refuses `.env`-like / keystore / secret files.
- Refactor engine refuses paths under `.agent/`; planner prompts forbid it.
- Every change is gated: per-file syntax check during refactor, then a
  tree-wide `verify()` before anything is committed. Failure ⇒ revert.
- The refactor engine never runs shell commands — it only rewrites file
  contents, so it cannot escalate a prompt into arbitrary execution.

## Extending

- **New static check**: add a `*_findings()` in `runner.py` returning
  `{type, severity, file, line?, message}` and include it in `analyze()`.
  Give the finding a `fixable` flag or register its type in
  `refactor.ATTEMPT_TYPES` to route it through the LLM fix engine.
- **New safe auto-fix class**: extend `refactor.py` — scoring lives in
  `BASE_SCORES`/`SEVERITY_MULTIPLIER`, the fix protocol in `refactor_one`.
- **New report section**: extend `drive_sync.compose_report()` (single source
  of truth for logs + Drive).
- Manual run: `python .agent/runner.py --mode analyze-only` (needs a git
  checkout with the branch reachable and, for full modes, `NVIDIA_API_KEY`).
