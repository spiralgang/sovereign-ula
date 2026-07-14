# Sovereign Ula ft sovereign edgepanel services

A **separate Android app** (package `com.sovereign.ula`) — **FEATURING ('sovereign-edgepanel-services')** that rebrands the
**UserLAnd (`tech.ula`) runtime** under our own name, icon, and package — while keeping
UserLAnd's full runtime intact (MainActivity, ServerService, UlaDocProvider, Termux
activity/service). It adds:

- A **full settings page** enumerating the entire requested permission suite, with deep
  links into Android's per-permission screens.
- **Direct access to shared storage / Downloads** (`MANAGE_EXTERNAL_STORAGE`, `MANAGE_MEDIA`,
  `OPEN_DOCUMENT_TREE`).
- An **edge panel** — a foreground overlay service (`EdgePanelService`) <- **A.K.A 'SOVEREIGN EDGEPANEL SERVICES'** with buttons to open
  settings, grant all permissions, and open Downloads.
- **Paid billing DISABLED** (meta-data `com.sovereign.BILLING_DISABLED = true`; no billing
  client is initialised).
- **Mandatory signing certificate** (`SoveApplication` aborts unless signed by the release
  cert).

## How it's built

The base APK (`base/ula-app.zip`, the original UserLAnd app) is decoded with apktool, the
package `tech.ula` is renamed to `com.sovereign.ula` across smali + resources, our
overlay (manifest, settings, edge panel, Java) is applied, our Java is compiled and merged
into the dex, and the APK is signed and published as a GitHub Release — all via
`.github/workflows/build.yml` on GitHub Actions. The runner has the full Android SDK, so the
local no-SDK limitation does not apply.

## Running it

Install the APK from the latest **Release**. Android sees it as its own app, distinct from
UserLAnd. Grant the requested permissions from Settings > App info; enable the edge panel services
from the in-app settings.
