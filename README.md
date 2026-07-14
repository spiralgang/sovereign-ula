# SOVEREIGN-ULA

![SOVEREIGN-ULA](images/sov_hero.jpeg)

**SOVEREIGN-ULA** is a rebrand of the UserLAnd (`tech.ula`) Linux-in-a-box runtime,
packaged as a **separate Android app** under our own name, icon, and package
(`dev.soveriegn.ula`). The full UserLAnd runtime stays intact (MainActivity,
ServerService, UlaDocProvider, Termux activity/service) — it just installs and runs
on its own, distinct from stock UserLAnd.

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
