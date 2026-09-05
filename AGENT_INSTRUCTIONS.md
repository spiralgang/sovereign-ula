# AGENT_INSTRUCTIONS.md

You are working in `spiralgang/sovereign-ula`.

## What this repo is
**The goal is the Sovereign ULA app** — a rebrand of the open-source UserLAnd
Android app (tech.ula runtime) into a separate app called **SOVEREIGN-ULA**
(package `dev.soveriegn.ula`). The stock UserLAnd runtime (terminal,
filesystem/session management, ServerService, UlaDocProvider) is kept intact; we
only swap `applicationId` so it installs separately.

## The unique features we add on top (don't break these)
- `Sovereign Edge Panel` settings category in `SettingsFragment` (full permission
  list, Downloads/shared-storage, overlay permission, edge-panel toggle).
- `EdgePanelService` — floating settings edge-panel overlay.
- `SovereignApplication` — mandatory signing-certificate enforcement (kills the
  process if signed by any cert other than the mandated release cert).
- Ubuntu 24.04 (Noble) as the default / auto-bootstrap distribution.
- Billing disabled (no `com.android.vending.BILLING`).

## How the rebrand is assembled (context)
This is a **repackage + rebrand of the ULA dex, not a from-scratch app**. The deliverable is ONE
separate app (`dev.soveriegn.ula`) carrying OUR name/icon/settings/edge-panel that still
RUNS UserLAnd's runtime (Termux/ULA `ServerService`, `UlaDocProvider`, filesystem, terminal) —
not merely a settings shell. We keep the entire tech.ula runtime intact and only swap
`applicationId` (plus add the unique features above) so it installs distinctly from `tech.ula`.

The original blocker: assembling a renamed Android app needs `android.jar` + `d8`/`aapt2` and,
to rename the package across the dex, `baksmali`/`smali`. That toolchain is absent in this local
env (local `aapt2` crashes on a missing `lib7z.so`). **Resolution: the build is outsourced to
GitHub Actions** — the runner has the full SDK + network, so Gradle assemble + sign + release
happens there, not locally. Don't try to compile the APK on this machine; push and let CI do it.

## First, read these
- `RULES.md` — hard constraints (toolchain versions, signing, what must not break).
- `PLANS.md` — goal, pipeline, current status, remaining work.

## Build locally (for fast iteration)
```
export ANDROID_HOME=/opt/android-sdk   # or your SDK
export ANDROID_NDK_HOME=$ANDROID_HOME/ndk/21.4.7075529
echo "sdk.dir=$ANDROID_HOME" > local.properties
./gradlew assembleRelease --no-daemon
```
Then sign:
```
$ANDROID_HOME/build-tools/29.0.3/apksigner sign --ks keystore.jks \
  --ks-key-alias sovereign --out app-release-signed.apk \
  app/build/outputs/apk/release/app-release-unsigned.apk
```

## CI (the source of truth for "does it build")
`.github/workflows/build.yml` runs on `ubuntu-latest`. It installs the SDK manually
(pinned old platforms), builds, signs with secrets, publishes a Release. Trigger via
`gh workflow run` or push to `master`. Watch with `gh run watch`.

## Known compile pitfalls (already hit, do not reintroduce)
- Never reference `Build.VERSION_CODES.R`/`Q` symbols by name when compileSdk=29 and the
  file imports `tech.ula.R` — the simple name `R` clashes with the resource class.
  Use `Build.VERSION.SDK_INT >= 30` / `>= 29` integer literals instead.
- `Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION` is API 30 — use the string
  literal `"android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION"` on SDK 29.
- Classes in `tech.ula.ui` must import `tech.ula.MainActivity` explicitly (no parent-package
  auto-import in Kotlin).

## Definition of done for a change
1. `./gradlew assembleRelease` succeeds (or the CI run is green).
2. No new `e:` Kotlin errors, no aapt resource errors.
3. Signed APK publishes to a GitHub Release.
4. `RULES.md`/`PLANS.md` updated if behavior changed.
