# SOVEREIGN-ULA

![SOVEREIGN-ULA](images/sov_hero.jpeg)

**SOVEREIGN-ULA** is a rebasing of UserLAnd (`tech.ula`) Linux-in-a-box shell enviroment,
packaged as a **separate unique distinctly reimagined apk** under our own name, icon, and package
(`dev.soveriegn.ula`). The UserLAnd shell runtime concept is intact (MainActivity,
ServerService, UlaDocProvider, Termux activity/service) — this just installs and runs
on its own settings, theme, process, evolved concept && updated defined bootstrap packages-distinct from stock UserLAnd (This is essentially what Termux is of UserLAnd what Sovereign-Ula is of UserLAnd— *rebased && reimagined*)

## Unique features we add on top

- **Sovereign settings screen** — enumerates the entire requested permission suite
  with deep links into Android's per-permission screens.
- **Sovereign Edge Panel** — a Samsung-style swipe-out edge panel (a slim handle on
  the right screen edge that expands into the full settings panel) with buttons to
  open settings, grant all permissions, manage all-files access, overlay permission,
  accessibility, and Downloads.
- **No funding popups** — the stock UserLAnd contribution/donation prompt is removed.
- **In-app billing disabled** — no billing client is initialised.
- **Mandatory signing certificate** — the app aborts unless signed by our release cert.
- **Arch Linux** as the default / auto-bootstrap distribution.
- **Aarch64 Compatible Translator** Updated && evolved packages
- **A.G.I Prepped** A.I services prepped on bootstrap
- **Settings Walk-Thru** MOTD HEADER WALK-THRU OF SETTINGS AND HOW TO ACCESS THEN
- **DEVICE IMPORT-EXPORT** IMPORT-EXPORT DEVICE FILES
- **ACCESSIBILTY SUITE PERMISSIONS** ANDROID PERMISSIONS ACCESSIBILITY PERMISSIONS
- **SHELL EVOLUTION && HARDENING** EVOLVING && HARDENING EXISTING SHELL && ENVIROMENT 
- **PRESET DEV ENVIRONMENT CONFIGS** READY-TO-USE PRESET ENVIRONMENT FOR DEVELOPER CONFIGURATIONS
  ##*PLUS MUCH, MUCH MORE*
---
---
---
## How it's built

Fork of UserLAnd; we change only `applicationId` to `dev.soveriegn.ula` and add the
Sovereign features above. GitHub Actions (`.github/workflows/build.yml`) runs on
`ubuntu-latest` with the full Android SDK + NDK, builds with Gradle, signs the APK
with our release keystore, and publishes it as a GitHub Release. No local SDK is
required — the heavy lifting happens on the runner.

## Running it

Install the APK from the latest **Release**. Android sees it as its own app, distinct
from UserLAnd. Grant the requested permissions from Settings > App info; enable the
edge panel and accessibility service from the in-app settings.
