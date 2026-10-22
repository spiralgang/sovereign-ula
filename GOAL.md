# GOAL.md — Sovereign ULA

## One-line goal
A self-sovereign, separately-installed Android app (`dev.soveriegn.ula`) that runs a
modern **Ubuntu 24.04 (Noble)** Linux environment on-device via proot, pre-loaded with
the command/agent/cloud tooling needed to deploy AI agents and cloud environments —
built better and smarter than the 8-year-old UserLAnd bootstrap it descends from.

## Non-goals
- We do NOT reimplement the UserLAnd runtime. We keep `tech.ula` intact and only rebrand
  + extend it.
- We do NOT bundle the distro `tar.gz` inside the APK. The APK releases as usual; the
  bootstrap `tar.gz` is built on-demand by the `distro-deploy-listener` workflow when the
  user picks a distro in-app.

## Success criteria
1. Signed APK releases from `build.yml` to a GitHub Release.
2. New filesystem auto-selects **Ubuntu 24.04 (Noble)** and is ready to autolaunch.
3. Rootfs is pulled from `sovereign-ula` releases tagged with the distro name (published by
   `distro-deploy-listener.yml`; no external assets org needed at runtime).
4. First-boot MOTD walk-through renders with `sov_hero` as the background; shows
   permissions deep-links, shared-storage mounts, pre-seeded packages, licensing/funding.
5. `sov_hero.jpeg` is the single artwork across launcher + all thumbnails + MOTD.
6. AI Agent PR Review runs automatically on every PR and posts a real LLM review.
7. aarch64 glibc packages (termuxvoid) run natively via the translation shim.
8. Env can never be SSH-locked-out (device-IMEI anchored SSH + original dropbear, both up).

## Design principles (from SOUL.md)
- Full-stack / production-ready, no mocks or placeholders.
- Delegated, agentic, linearly traceable development.
- Cloud-offload heavy work to GitHub Actions runners.
