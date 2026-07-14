# RULES.md — Sovereign EdgePanel build repo

## Hard constraints
- This repo is a FORK of CypherpunkArmory/UserLAnd, rebranded to a separate app.
- `applicationId` = `com.sovereign.edgepanel` (CHANGED). Java package stays `tech.ula`
  (the runtime dex/classes are untouched — only the app identity differs). Do NOT rename
  the `tech.ula` Java package; only rebrand via applicationId + manifest + resources.
- Build toolchain is OLD and fragile:
  - Gradle 5.1.1 wrapper, AGP 3.4.3, Kotlin 1.3.61, JDK 8.
  - compileSdk/targetSdk = 29. Do NOT bump to 30+ unless you also upgrade Gradle+AGP+Kotlin.
  - Use `build-tools;29.0.3` and the PINNED old platforms (android-28 r06, android-29 r04)
    because newer platform zips contain `extension-level`/`api-level 34x` metadata that
    AGP 3.4.3's aapt2 cannot parse.
- NDK 21.4.7075529 is REQUIRED (terminal-emulator compiles JNI `termux.c`). Set
  `ANDROID_NDK_HOME` to it or the `:terminal-emulator` config throws NullPointerException.
- Release APK is built UNSIGNED (`assembleRelease`), then signed by the CI with `apksigner`
  using the keystore from repo secrets. Do NOT add a `signingConfig` to the release
  buildType (caused `validateSigningRelease` failure).

## Signing / secrets (NEVER inline)
- SOVEREIGN_KEYSTORE_BASE64, SOVEREIGN_KEY_ALIAS, SOVEREIGN_KEYSTORE_PASSWORD,
  SOVEREIGN_KEY_PASSWORD are GitHub Actions secrets.
- The mandatory release cert SHA-256 is hardcoded in
  `app/src/main/java/tech/ula/SovereignApplication.kt` (REQUIRED_CERT_SHA256). If you
  rotate the keystore, update BOTH the secret AND that constant.

## What must stay working
- tech.ula runtime (MainActivity, ServerService, UlaDocProvider, termux terminal).
- Sovereign additions: SettingsFragment "Sovereign EdgePanel" category, EdgePanelService
  overlay, mandatory signing enforcement, Arch as default distro.

## Do not
- Do not commit `keystore.jks` or any keystore (gitignored).
- Do not add `com.android.vending.BILLING` — billing is intentionally disabled.
- Do not run `ktlint`/`lint` as required gates in CI (they break the old toolchain).
