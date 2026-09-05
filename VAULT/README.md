# VAULT — Sovereign ULA

Operational notes, decisions, and secrets-handling references. Do NOT put raw
secret values here — only pointers.

- `VAULT/CODEBASE-AUDIT.md` — section-by-section master audit (2026-09-05) +
  the wave-by-wave completion plan to reach a green, self-consistent codebase.

## Repo secrets (GitHub Actions → Settings → Secrets and variables → Actions)
- `SOVEREIGN_KEYSTORE_BASE64` — release keystore (base64). Decode + sign in build.yml.
- `SOVEREIGN_KEY_ALIAS` / `SOVEREIGN_KEYSTORE_PASSWORD` / `SOVEREIGN_KEY_PASSWORD`.
- `NVIDIA_API_KEY` — used by the AI Agent PR Review runner + Hermes Autonomous
  Runner (NIM LLM calls).
- `GEMINI_API_KEY` / `GENAI_MODEL` — optional free-tier backend for Hermes
  (Google GenAI; default model `gemini-2.5-flash`). Provider auto-selects
  NVIDIA when both keys exist; force with `LLM_PROVIDER=gemini`.
- Free-endpoint LLM chain (AI Agent PR Review + FSM Enforcer review):
  `NVIDIA_API_KEY` → `GEMINI_API_KEY` → `GROQ_API_KEY` → `OPENROUTER_API_KEY`
  → `HF_TOKEN` — first configured key wins, all OpenAI-compatible free tiers.
  `VIBE_API_KEY` remains accepted as a legacy NVIDIA alias. No OpenAI anywhere.
- `LLM_PROVIDER` — optional `nvidia` | `gemini` override (workflow input too).
- `GDRIVE_CREDENTIALS` / `GDRIVE_FOLDER_ID` — Google service-account JSON
  (base64) + Drive folder for Hermes run-report backups.
- `VIBE_API_KEY` — alternate LLM key, same purpose.
- `HERMES_HUB_KEY` — fine-grained GitHub PAT (admin) used by local agent tooling + pushes.
- `LLM_BASE_URL` / `LLM_MODEL` — optional overrides for the review model (unset = NVIDIA default).

## Key decisions (traceable)
- Assets are SELF-HOSTED in this repo: distro rootfs/assets published by
  distro-deploy-listener.yml to sovereign-ula releases (tag = distro name); apps
  catalog at apps/apps.txt. Build-time native libs still come from
  CypherpunkArmory/UserLAnd-Assets-Support@v1.5.1 (only publisher of those zips).
- Default distro arch → ubuntu (Noble). The universal base env (Arch/Alpine + proot) is
  what builds the chroot; the chosen distro rootfs is overlaid on top.
- SELinux: disabled inside the env via ld.so.preload shim (SECONDARY) AND a virtual-kernel
  proot design (PRIMARY). Both present.
- SSH: BOTH the new device-IMEI anchored SSH (2023) and the original dropbear (2022) run
  concurrently. Original dropbear config preserved verbatim as source-of-truth fallback.

## Build / release
- `build.yml` → assembleRelease (unsigned) → apksigner → Release APK.
- `distro-deploy-listener.yml` → app-triggered `workflow_dispatch` builds chosen distro tar.gz.
- `ai-agent-review.yml` → LLM reviews PR diffs on open/sync (skips drafts).
- `autonomous-agent.yml` → Hermes runner on a 30-min cron (analyze → NIM plan →
  apply → verify → draft PR → Drive report). See `.agent/runner.py`. LLM
  backend: NVIDIA NIM or Google GenAI free tier (streaming) — see `.agent/nim_client.py`.
- `bootstrap/core/agent-tooling/` → agentic-coder layer baked into every distro
  rootfs: Antigravity CLI (`agy`, successor to the retired Gemini CLI) + uv-managed
  `google-genai` venv + Node 22 (NodeSource) + globally installed MCP servers
  (filesystem/github/context7) wired into `~/.gemini/config/mcp_config.json`.
- `agent-verifier-matrix.yml` → matrix of independent checks (FSM / shell /
  python / yaml / secrets) run on every Hermes draft PR head; output-defined
  matrix via `fromJSON` (`.agent/jobs.py` = verify-until-green job engine).

## Local agent env
- `~/.hermes/.env` holds HERMES_HUB_KEY, NVIDIA_API_KEY, VIBE_API_KEY (written by agent).
- `~/.bashrc` exports the same for interactive shells.
- `~/.git-credentials` stores the PAT for git push.
