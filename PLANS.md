# PLANS.md — Sovereign ULA

## Goal
**The Sovereign ULA app is the goal**: a fully rebranded build of the UserLAnd
(tech.ula) Linux-in-a-box runtime, packaged as a separate Android app under our
name (package `dev.soveriegn.ula`, app name "SOVEREIGN-ULA").

The **unique features** we add on top of the stock UserLAnd runtime are:
- Our own **Sovereign settings screen** (a full "Sovereign Edge Panel" preference
  category enumerating every permission the app can request, plus direct
  shared-storage / Downloads access).
- A floating **edge-panel overlay** service (EdgePanelService).
- **In-app billing disabled** and **mandatory signing-certificate enforcement**
  (SovereignApplication refuses to run if not signed by our release cert).
- **Ubuntu 24.04 (Noble) as the default / auto-bootstrap distribution.**

Everything else (the terminal, proot/PRoot filesystem management, the
`ServerService`, `UlaDocProvider`, session handling) is the stock UserLAnd
runtime that we keep intact — we only change `applicationId` so it installs as a
distinct app; the `tech.ula` Java package and its dex stay untouched.

## Why fork instead of apktool surgery
Earlier attempts used apktool to patch the compiled APK (rename smali, hand-edit binary
AXML). That is fragile and strips the runtime. Forking the open-source source and changing
only `applicationId` keeps the entire tech.ula runtime intact while producing a genuinely
separate installable app. This is the correct, reproducible approach.

## How the rebrand is assembled (historical context + the actual blocker)
- This is a **repackage + rebrand of the ULA dex, not a from-scratch app**. The goal is ONE
  separate app (`dev.soveriegn.ula`) with OUR name/icon/settings/edge-panel that still
  RUNS UserLAnd's runtime (Termux/ULA services, filesystem, terminal) — not just a settings
  shell. So we take the ULA app, rebrand it (new package, our name/icon, our full settings +
  edge panel), keep its entire runtime intact, and ship that as a distinct APK Android
  recognizes separately from `tech.ula`.
- The blocker was always toolchain: to assemble it we need `android.jar` + `d8`/`aapt2`, and
  a full aapt-based build needs the SDK. `java`/`apktool` are present locally but apktool alone
  only rebuilds resources+manifest; to *change the package name* you must rewrite `tech.ula.*`
  references across the dex — which needs `baksmali`/`smali` (disassemble -> edit -> reassemble).
  That toolchain is absent here (and `aapt2` locally crashes on a missing `lib7z.so`).
- **Resolution: outsource assembly to GitHub Actions.** The runner has the full SDK + network,
  so the build happens there. The original plan was: workflow downloads the base ULA APK,
  decodes with apktool (emits smali on a normal machine), renames `tech.ula` ->
  `dev.soveriegn.ula` across smali + manifest + resources, injects our
  settings/edge-panel, rebuilds, signs, releases. We ultimately used the cleaner **fork-the-source**
  path (same outcome, less fragility), but the principle holds: the heavy lifting is done by
  runners, not this local env.

## Rebrand deliverables (what was committed)
- `base/` — original ULA APK staged for reference.
- `overlay/AndroidManifest.xml` — our manifest: package `dev.soveriegn.ula`, our app name,
  full permission suite, settings + edge-panel service, `billing-off` + `signing-required` meta.
- `overlay/res/...` — our settings `PreferenceScreen`, edge-panel layout, strings, icon, app name.
- `.github/workflows/build.yml` — build / rename / sign / release pipeline.
- `README.md` — explains it is a rebrand of ULA's runtime under our package.

## Build pipeline (GitHub Actions, ubuntu-latest)
1. Checkout.
2. JDK 8 (temurin).
3. Manual Android SDK install: cmdline-tools, platform-tools, build-tools;29.0.3,
   NDK 21.4.7075529, pinned old platforms android-28_r06 + android-29_r04, write
   `local.properties` with `sdk.dir`.
4. `./gradlew assembleRelease --no-daemon` -> unsigned `app-release-unsigned.apk`.
5. Decode keystore from secret, `apksigner` sign.
6. `apksigner verify`.
7. Publish signed APK as a GitHub Release (softprops/action-gh-release).

## Current status (as of 2026-07-15)
- applicationId, app_name, permissions, Sovereign settings category, EdgePanelService,
  SovereignApplication (signing enforcement) — ALL authored.
- Default distro switched **arch -> ubuntu (Noble 24.04)**.
- Assets org repointed **CypherpunkArmory -> spiralgang**.
- `sov_hero.jpeg` is now the single branding image (launcher/round/foreground/notification
  icons regenerated from it; in-app MOTD background).
- Modern Noble bootstrap authored under `bootstrap/ubuntu/` (rootfs builder, BOTH
  selinux designs, BOTH SSH designs w/ IMEI anchor). The universal /support layer,
  `sovereign-motd.sh`, and the glibc/termuxvoid shim live in **`bootstrap/core/`**
  (FSM agnostic core — distro dirs carry only distro config; the FSM enforcer's
  preflight passes).
- CI: SDK setup + Gradle build + sign + release (build.yml). NEW: `ai-agent-review.yml`
  (LLM PR review runner) + `distro-deploy-listener.yml` (app-triggered distro tar.gz build).
- AI Agent PR Review workflow runs green against the NVIDIA LLM (model meta/llama-3.1-8b-instruct).
- Hermes Autonomous Runner (`autonomous-agent.yml` + `.agent/`) runs on a 30-minute
  cron: analyze → NIM LLM plans one improvement → apply on `hermes-autonomous` →
  verify → draft PR → report to `.agent/logs/` + Google Drive.

## Remaining work
- [x] Get `assembleRelease` to produce a signed APK and a published Release (build.yml does this).
- [x] Distro assets are SELF-HOSTED: `distro-deploy-listener.yml` publishes the Noble rootfs +
      assets to `sovereign-ula` releases tagged with the distro name (ubuntu | debian | arch);
      the app fetches them by tag (GithubApiClient `releases/tags/<distro>`). The apps catalog
      (`apps/apps.txt`) is rebased into THIS repo — no `UserLAnd-Assets-*` dependency at runtime.
- [x] (was issue #58) termuxvoid shim + the whole universal support layer moved to
      `bootstrap/core/` — the FSM enforcer preflight passes.
- [x] In-app "deploy distro -> workflow_dispatch" is DROPPED (an on-device dispatch needs a
      PAT; instead `distro-deploy-listener.yml` is run on demand and the app pulls the resulting
      tagged releases — see GithubApiClient).
- [ ] Add in-app "update available" prompt (optional, user-driven).
      Design: stamp the release tag into the APK at build time (build.yml passes
      `-PsovereignVersionName=v1.0.${{ github.run_number }}`; defaultConfig reads the property,
      defaulting to `2.8.3`), then MainActivity compares GitHub `releases/latest` with
      `BuildConfig.VERSION_NAME` and offers an optional download dialog. Needs a CI-verified
      pass — the APK only ever compiles on the runner.
- [ ] Ship per-app icons/scripts under `apps/<name>/` (apps.txt lists firefox/git/vim; the
      fetcher looks for `<name>.png/.txt/.sh` beside the catalog).
- [ ] (Roadmap) glibc/termux shim hardening + smart auto-bundle package manager; Drive backup
      for Hermes run reports is wired (GDRIVE_CREDENTIALS / GDRIVE_FOLDER_ID secrets).

## Environment quirks to remember
- GitHub Actions runners run Node 24; actions/checkout@v4 + setup-java@v4 print a
  harmless Node 20 deprecation warning.
- `malinskiy/action-android@v1` does NOT exist — do not use it.
- `android-actions/setup-android@v3` installs a cmdline-tools that fails under JDK 8;
  the manual SDK install in the workflow is the reliable path.
