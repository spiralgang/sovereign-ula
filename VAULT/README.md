# VAULT — Sovereign ULA

Operational notes, decisions, and secrets-handling references. Do NOT put raw
secret values here — only pointers.

## Repo secrets (GitHub Actions → Settings → Secrets and variables → Actions)
- `SOVEREIGN_KEYSTORE_BASE64` — release keystore (base64). Decode + sign in build.yml.
- `SOVEREIGN_KEY_ALIAS` / `SOVEREIGN_KEYSTORE_PASSWORD` / `SOVEREIGN_KEY_PASSWORD`.
- `NVIDIA_API_KEY` — used by the AI Agent PR Review runner (LLM calls).
- `VIBE_API_KEY` — alternate LLM key, same purpose.
- `HERMES_HUB_KEY` — fine-grained GitHub PAT (admin) used by local agent tooling + pushes.
- `LLM_BASE_URL` / `LLM_MODEL` — optional overrides for the review model (unset = NVIDIA default).

## Key decisions (traceable)
- Assets org repointed CypherpunkArmory → spiralgang (GithubApiClient.kt, GithubAppsFetcher.kt).
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

## Local agent env
- `~/.hermes/.env` holds HERMES_HUB_KEY, NVIDIA_API_KEY, VIBE_API_KEY (written by agent).
- `~/.bashrc` exports the same for interactive shells.
- `~/.git-credentials` stores the PAT for git push.
