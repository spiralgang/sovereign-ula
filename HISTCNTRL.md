# HISTCNTRL.md — Sovereign ULA rebrand approach & control notes

Control file: captures the rebrand strategy and the deliverables so any agent or
future session can reconstruct intent without re-deriving it.

## Core decision (the goal, stated once)
This is a **repackage + rebrand of the ULA dex, not a from-scratch app**.
Deliverable: ONE separate app, package `dev.soveriegn.ula`, carrying OUR
name / icon / full settings / edge-panel, that still **RUNS UserLAnd's runtime**
(Termux/ULA `ServerService`, `UlaDocProvider`, filesystem, terminal). It is NOT a
settings shell — it MUST embed the ULA runtime AND our settings + edge panel.
Android must recognize it as distinct from `tech.ula`.

## The original blocker (why it couldn't be done locally)
- Assembling a renamed Android app needs `android.jar` + `d8`/`aapt2`; a full
  aapt-based build needs the SDK.
- `java`/`apktool` are present locally; apktool rebuilds resources+manifest fine.
- But to truly change the package name you must rewrite `tech.ula.*` references
  **across the dex**, which needs `baksmali`/`smali` (disassemble -> edit ->
  reassemble). That toolchain is absent locally (local `aapt2` crashes on a
  missing `lib7z.so`).
- Resolution: **outsource assembly to GitHub Actions** — the runner has the full
  SDK + network. The build/sign/release happens there, not on this machine.

## The apktool-rename pipeline (documented plan)
The GitHub workflow will:
1. Download the original ULA APK (staged in repo as `base/ula-app.zip`).
2. Decode with `apktool` (on the runner, apktool emits smali normally — the
   earlier local failure was a quirk).
3. Rename `tech.ula` -> `dev.soveriegn.ula` across smali + manifest +
   resources.
4. Inject our settings / edge-panel.
5. Rebuild with `apktool`, sign with the repo-secret keystore, release.

Runner installs apktool by fetching `apktool` 3.x jar (network is available on
the runner), or via apt/brew — do NOT rely on the broken local copy.

## Local job (what was committed)
1. `.github/workflows/build.yml` — the build / rename / sign / release pipeline.
2. `base/ula-app.zip` — the original ULA APK (staged for reference / decode).
3. `overlay/AndroidManifest.xml` — our manifest: package `dev.soveriegn.ula`,
   our app name, full permission suite, settings + edge-panel service,
   `billing-off` + `signing-required` meta. ULA's runtime components
   (`MainActivity`, `ServerService`, `UlaDocProvider`, Termux activity/service)
   are KEPT — only the package identity changes.
4. `overlay/res/...` — our settings `PreferenceScreen`, edge-panel layout,
   strings, icon, app name, theme.
5. `README.md` — explains it is a rebrand of ULA's runtime under our package.

## Actual resolution used (deviation from apktool plan)
We ultimately built via **fork-the-source** (same outcome, less fragility): fork
UserLAnd, change only `applicationId` to `dev.soveriegn.ula`, add the
Sovereign features (settings category, EdgePanelService overlay,
SovereignApplication signing enforcement, Arch default, billing-off), then let
GitHub Actions run `./gradlew assembleRelease` + `apksigner` + Release. See
`PLANS.md` / `AGENT_INSTRUCTIONS.md` for the live build. The apktool-rename
approach above remains valid if a pure-APK rebrand is ever required.

## Status
- Build GREEN on `ubuntu-latest`; signed APK published to GitHub Releases
  (package `dev.soveriegn.ula`, launches `tech.ula.MainActivity`).
- Open: optional in-app "update available" prompt (Release feed + cert-verified
  install).
