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
- **Arch Linux as the default / auto-bootstrap distribution.**

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

## Current status (as of last edit)
- applicationId, app_name, permissions, Sovereign settings category, EdgePanelService,
  SovereignApplication (signing enforcement), Arch default — ALL authored.
- CI: SDK setup + Gradle build + sign + release wired.
- Blocked on: one Kotlin compile error (`R` resource-class clash with
  `Build.VERSION_CODES.R`); fix = use `Build.VERSION.SDK_INT >= 30` instead of
  `VERSION_CODES.R`. (Patch already applied locally; verify green on next run.)

## Remaining work
- [ ] Get `assembleRelease` to produce a signed APK and a published Release.
- [ ] Add in-app "update available" prompt (optional, user-driven) that checks a
      release feed and offers to download/install the latest APK.
- [ ] (Roadmap) Gemini-tracked: glibc/termux shim compat + smart auto-bundle package
      manager (nala/aptly/aptitude, bash/apt completions, community repos, dedup
      symlink storage, separate user namespace for command isolation).

## Environment quirks to remember
- GitHub Actions runners run Node 24; actions/checkout@v4 + setup-java@v4 print a
  harmless Node 20 deprecation warning.
- `malinskiy/action-android@v1` does NOT exist — do not use it.
- `android-actions/setup-android@v3` installs a cmdline-tools that fails under JDK 8;
  the manual SDK install in the workflow is the reliable path.
