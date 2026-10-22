# CODEBASE AUDIT — sovereign-ula (master)

Audited: **2026-09-05** — HEAD `origin/master = e2d02aa` (PR #60 "FSM removes the
violation"; parent `343cfc7` = last CI-built release state, v1.0.70 era).
Local working tree = `343cfc7` + a large **uncommitted fix-set** built across
prior work sessions (see §Plan — none of it is on master yet).

Verdict up front: **master is release-stale, self-contradicting, and its own CI
is partially dead.** Releases through v1.0.70 are sound; everything authored
after that era (AI-review workflow rework, Hermes agentic runner, FSM
restructure, Kotlin dedupe, docs sync, distro agent layer) exists only as local
uncommitted changes. No open PRs/branches exist on the remote — the fixes are
waiting to be Saved/pushed from this workspace.

Evidence methods: `git ls-tree/show` against `origin/master`, PyYAML parse of
every `.github/workflows/*`, a faithful re-run of the FSM preflight in
`hermes_fsm_enforce.yml` against master's `bootstrap/`, duplicate-declaration
greps on the Kotlin/Gradle sources.

---

## 1. Section-by-section status

| # | Section | Health | Headline gaps |
|---|---------|--------|---------------|
| 1 | Governance & docs | 🔴 DRIFT | PLANS.md self-contradictory & stale (says Arch default at line 15, Ubuntu at line 70); README.md and AGENT_INSTRUCTIONS.md still claim **Arch Linux default**; only GOAL.md says Ubuntu Noble. |
| 2 | Android app (Kotlin) | 🔴 BLOCKED | Compile-blocking duplicate declarations confirmed on master: `getReleaseToUseForRepo` ×2 (`GithubApiClient.kt`), `val baseUrl` ×2 (`GithubAppsFetcher.kt`), duplicate `def assetVersion/baseUrl` block in `app/build.gradle`. Master's last CI build predates these edits. |
| 3 | Bootstrap / distros | 🟠 RED-CI | FSM violation remains: `bootstrap/ubuntu/input/termuxvoid-shim.sh` still committed → master fails its own `hermes_fsm_enforce.yml` preflight (simulated: 1 violation). PR #60 only added build-staging + docs (2 files, 0 deletions). |
| 4 | CI/CD workflows | 🔴 BROKEN | `ai-agent-review.yml` and `distro-deploy-listener.yml` fail YAML parse → both workflows are **dead on GitHub** (PR review gate + in-app distro deploys silently not running). Duplicate FSM enforcer present under a filename ending in a literal newline. Non-workflow junk in the dir (`create.py`, `run_ula_job.py`). CodeQL matrix still scans **ruby** (no Ruby source; only fastlane `Gemfile.lock`). |
| 5 | Agentic tooling | ⚪ LOCAL-ONLY | `.agent/` runner suite (dual-provider LLM client, refactor engine, verify-until-green jobs, knowledge base, Drive backup) + `autonomous-agent.yml` + `agent-verifier-matrix.yml` + `bootstrap/core/agent-tooling/` (agy/uv/MCP) exist only in the working tree. |
| 6 | Assets / apps / release | 🟡 HYGIENE | `decoded/` (0.8 MiB, 757 files of APK decode incl. `META-INF/`) is committed — noise/duplication vs `termux-app/` sources; decide keep-vs-untrack. `fastlane/` 2.2 MiB (screenshots) OK. `images/sov_hero.jpeg` = single artwork ✓. `apps/apps.txt` self-hosted catalog ✓. |
| 7 | Security & secrets | 🟢 CLEAN* | No hardcoded keys in tracked files (scans clean). *Earlier leaked `nvapi-…` key was never committed — revoke if not already. Release keystore lives only in secrets. |
| 8 | Tests & quality gates | 🟡 THIN | 24 app unit-test files exist but no workflow runs them; verifier-matrix (local-only) would be the static gate. |

### 1.1 Governance & docs — details
- `PLANS.md` is internally contradictory and ~6 weeks stale ("as of 2026-07-15",
  Arch default + old apktool narrative), missing: assets self-hosting flow,
  distro-deploy listener, Hermes/agent additions, FSM layout, GenAI/agy layer.
- `README.md` & `AGENT_INSTRUCTIONS.md`: Arch bullets remain; AGENT_INSTRUCTIONS
  still lists the old "repackage the dex" pipeline and no agent-tooling/CI reality.
- `RULES.md` / `GOAL.md`: near-current (Ubuntu Noble, self-hosted assets) — minor
  wording drift only.
- Fix-set already written locally for every one of these docs (not committed).

### 1.2 Android app — the two duplicate blocks
Both files carry a half-finished org migration: an old copy stacked above the
intended new one (same-function duplicates → `assembleRelease` will fail). The
local fix-set keeps exactly one copy each (intended behavior: distro assets from
`sovereign-ula` releases tagged by distro name; apps catalog in-repo). This is
the single highest-risk item because the only place it compiles is CI.

### 1.3 Bootstrap / FSM — half-migrated
PR #60's stated intent (delete the duplicate; stage from `bootstrap/core/` at
build time) was not carried out: 0 deletions landed, so the banned copy is still
committed and any future bootstrap-touching PR is auto-rejected by the preflight.
Two coherent finishes exist:
- **(A, staged in local tree)** move the whole universal layer into
  `bootstrap/core/` (`support/`, `sovereign-motd.sh`, shim) and rewire
  `main.sh`/`Dockerfile`/`build.sh`/`docker-bake.hcl` to `/core/` — fully
  validated locally (0 violations).
- **(B, PR #60's path)** delete the committed `input/termuxvoid-shim.sh` (and
  siblings) and rely on the new build-time staging; smaller diff.
Either is fine; what is not fine is the current half-state.

Enforcer blind spot (must fix regardless): `find -maxdepth 2` skips
`input/support/*` (depth 3) — banned names there are invisible. The enforcer
also runs twice (duplicate file + newline-suffixed twin).

### 1.4 Workflows — the dead ones
PyYAML on master's `.github/workflows/`:
- `ai-agent-review.yml` → parse error (`mapping values are not allowed`) — LLM PR
  review silently off.
- `distro-deploy-listener.yml` → parse error — the app's in-app "deploy distro"
  dispatch target silently off.
- `create.py`, `run_ula_job.py` → not workflows (misnamed script/transcript); junk.
- `run-gemini-cli.yml` → parses but is not a usable workflow.
- Duplicate enforcer: `Hermes-FSM-Enforcer-&-Agentic-Review.yml\n` (trailing
  newline in the filename).
- `codeql.yml`: Ruby in the matrix (no Ruby code; every run wastes ~minutes).

The local fix-set repairs all of these (rewritten `distro-deploy-listener.yml`
+ `ai-agent-review.yml`, `ai_review.py` splice repairs, removals, codeql
matrix cleanup, `create.py`→`create.md`) and was verified: **all workflows parse,
FSM preflight = 0** against the local tree.

### 1.5 Agentic tooling (local-only; the repo's "living code" layer)
- `.agent/` Hermes suite: analyze (FSM/syntax/secrets/TODO) → LLM fix engine →
  verify-until-green persistent jobs → knowledge base (history.jsonl + SQLite
  trends) → draft PRs on `hermes-autonomous` → Drive reports. LLM backend: NVIDIA
  NIM or **Google GenAI free tier with streaming** (agy is the interactive CLI,
  not the runner backend).
- Workflows: `autonomous-agent.yml` (cron `*/30`, mode/provider dispatch) and
  `agent-verifier-matrix.yml` (output-defined matrix of 5 checks on agent PRs).
- `bootstrap/core/agent-tooling/`: agy + uv-managed `google-genai` + Node 22
  (NodeSource) + globally installed MCP servers (filesystem/github/context7),
  config at `~/.gemini/config/mcp_config.json`. FSM-compliant (core), wired into
  the Ubuntu rootfs build, opt-out `SOVEREIGN_SKIP_AGENT_TOOLS=1`.

### 1.6 Assets / release hygiene
`decoded/` duplicates what `app/` + `termux-app/` sources already provide; 757
committed decode artifacts bloat diffs. Recommend `git rm -r --cached decoded`
+ `.gitignore decoded/` (keep locally for reference) once the merge wave lands —
owner decision. Everything else (single hero image, icon generator script,
fastlane metadata, self-hosted apps catalog) is consistent with GOAL.md.

---

## 2. Completion plan — master → green, then "perfection"

Merge waves below correspond 1:1 to files already in the local working tree
(Freebuff: Save/PR per wave; keep waves separable so each is independently
reviewable and each failure is attributable). No open PRs exist to merge — this
is the backlog to ship.

### Wave A — un-break CI (smallest, highest value)
Files: `.github/workflows/{ai-agent-review.yml, distro-deploy-listener.yml,
codeql.yml, hermes_fsm_enforce.yml, autonomous-agent.yml,
agent-verifier-matrix.yml}`, `.github/scripts/{ai_review.py, gemini_apk_edit.py,
agent_repo_fix.py}`, `create.py`→`create.md`, remove `run-gemini-cli.yml`,
`run_ula_job.py`, `Hermes-FSM-Enforcer-&-Agentic-Review.yml\n`.
Acceptance: PyYAML parses every workflow; CodeQL matrix = python/javascript/java
only; enforcer runs once; `agent-verifier-matrix.yml` green on this PR.
Risk: none (deletions + parse repairs). Blocks: everything downstream.

### Wave B — finish the FSM migration
Adopt approach (A) local rewire (already validated) or (B) PR #60 staging; then
delete every banned file from `bootstrap/ubuntu/input/`; fix the enforcer's
`-maxdepth 2` blind spot (scan `bootstrap/*/` recursively minus `core`).
Acceptance: simulated preflight = 0 violations on the merged tree; bootstrap
build step (docker-bake/build.sh dry check) unchanged semantics.

### Wave C — restore the compile
Files: `app/src/main/java/tech/ula/model/remote/GithubApiClient.kt`,
`GithubAppsFetcher.kt`, `app/build.gradle` (drop the duplicate copies; keep the
intended behavior).
Acceptance: `bun tsc`-equivalent not applicable → **CI `build.yml`
assembleRelease green** (authoritative; no JDK in this workspace). This is the
only wave whose proof is a CI run — do not merge Wave C without it.

### Wave D — sync governance docs
Files: `PLANS.md` (rewrite status/remaining per current flow), `README.md`,
`AGENT_INSTRUCTIONS.md`, `RULES.md`, `GOAL.md`, `VAULT/*`, `bootstrap/ubuntu/
README.md`, plus a `bootstrap/core/README.md` for the FSM layer.
Acceptance: zero Arch-default claims; PLANS matches master reality post Waves
A–C; single source of truth for build/test/release.

### Wave E — land the agentic layer (optional-but-requested)
Files: `.agent/` suite, `autonomous-agent.yml`, `agent-verifier-matrix.yml`,
`bootstrap/core/agent-tooling/**`, VAULT secrets doc rows.
Acceptance: workflow dispatch `mode: analyze-only` green without keys; with
`GEMINI_API_KEY` (free tier) a full cycle runs; distro rebuild (docker-bake)
bakes agy/uv/MCP with 0 FSM violations.
Needs: repo secrets `GEMINI_API_KEY` (or NVIDIA) — user action.

### Wave F — hardening & cleanliness (owner decisions marked ☐)
- ☐ `decoded/`: untrack + gitignore vs keep-as-artifact.
- ☐ Run unit tests in CI: add `./gradlew testDebugUnitTest` step to `build.yml`
  (24 test files exist, currently unexecuted).
- ☐ `fastlane/` metadata drift vs new app name/screenshots.
- ☐ Release feed + optional in-app update prompt (see
  `VAULT/future_implementations.md` §5 — design ready).
- ☐ Turn on branch protection: default branch read-only for agents; Hermes PRs
  require 1 approval + green verifier matrix.

### "Perfection" backlog (beyond green) — from VAULT/future_implementations.md
1. glibc/termux ↔ com.termux translation shim completion (termuxvoid v2).
2. Smart auto-bundle package manager (setup suggester, dedupe downloads).
3. Process + second-user isolation inside the env (containment/cgroup).
4. Virtual runtime containerization (zram, vGPU, cloud-backed storage) — research.
5. In-app update prompt (optional, cert-verified APK swap).
6. Hermes self-verification loop incl. job suites that run repo tests (Wave E
   extension: teach `.agent/jobs.py` verify_commands to invoke
   `./gradlew testDebugUnitTest` on a nightly job).

## 3. Standing guardrails (do not regress)
- `applicationId` = `dev.soveriegn.ula`; ULA runtime (tech.ula) intact.
- Build ONLY in GitHub Actions (no local assembleRelease in this env).
- Signing cert enforcement + secrets-only keystore; never inline keys.
- FSM: agnostic assets in `bootstrap/core/`, distro dirs carry config only.
- Default distro: Ubuntu 24.04 Noble. Assets: self-hosted releases, tag=distro.
- Agents: draft PRs on `hermes-autonomous`; never write default branch directly.
