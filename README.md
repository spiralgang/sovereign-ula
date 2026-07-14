# Sovereign ULA — custom image / mod worktree

Working artifacts for the sovereign ULA Android app mod:
- `env-toolchain.sh` — wires the rootless JDK17 + apktool + apksigner toolchain.
- `run_ula_job.py` — calls Gemini `gemma-4-31b-it` (real LLM) on the app to
  produce an edit plan (`mod/gemma_edit_plan.json`).
- `mod/gen_settings.py` — generates the FULL settings `PreferenceScreen`
  (enable-all-permissions, shared-storage/Downloads, billing-DISABLED,
  mandatory signing cert, accessibility/overlay/install toggles).
- `mod/edge_panel.xml` — Samsung-style swipe-out edge panel, filled with the
  full settings suite (the minimal `tech.ula` edge panel, maxed out).
- `mod/preferences_full.xml`, `mod/AndroidManifest.clean.xml` — manifest +
  prefs ground truth.
- `decoded/` — apktool decode of `ula-app.zip` (manifest, smali, res, assets).

## Build status
- Decode: OK. Manifest is plain-text XML (non-standard APK) so apktool `b`
  fails at manifest recompile — full rebuild needs Gradle/SDK or `aapt`
  manifest-rebuild. Signing requires the release keystore (NOT committed;
  set via GitHub secret / local file).
- Do NOT push broken `.apk` outputs. Rebuild on GitHub runners or via the
  documented toolchain, then sign with the keystore secret.

## Rebuild toolchain (rootless, this env)
source env-toolchain.sh   # needs rootfs/ (JDK17 from debs) + apktool.jar
python3 run_ula_job.py     # regenerate the Gemini edit plan
python3 mod/gen_settings.py
