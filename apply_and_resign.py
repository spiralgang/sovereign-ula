#!/usr/bin/env python3
"""Apply the model's manifest edits to the decoded ula APK, then rebuild + re-sign.
Safe, reversible: edits only AndroidManifest.xml (adds permissions + SettingsActivity
the Gemini plan specified), rebuilds with apktool, re-signs with the local keystore.
"""
import os, re, subprocess, sys

TC = os.getenv("TOOLCHAIN_DIR", os.path.expanduser("~/toolchain"))
DEC = os.path.join(TC, "work/ula_decoded")  # apktool-created root (has apktool.yml)
MANIFEST = os.path.join(DEC, "unknown/ula/AndroidManifest.xml")
KEYSTORE = os.path.join(TC, "keys/release.keystore")
APKTOOL = os.path.join(TC, "apktool.jar")
OUT_APK = os.path.join(TC, "work/ula_modified_unsigned.apk")
FINAL_APK = os.path.join(TC, "work/ula_modified_signed.apk")

NEW_PERMS = [
    "android.permission.MANAGE_EXTERNAL_STORAGE",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.QUERY_ALL_PACKAGES",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.WRITE_SETTINGS",
    "android.permission.READ_PHONE_STATE",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
]

def edit_manifest():
    txt = open(MANIFEST, encoding="utf-8").read()
    additions = []
    for p in NEW_PERMS:
        if p not in txt:
            additions.append(f'\t<uses-permission android:name="{p}">\n\t</uses-permission>')
    # add a SettingsActivity declaration if absent
    settings = ""
    if "SettingsActivity" not in txt:
        settings = (
            '\t\t<activity android:name="tech.ula.SettingsActivity" '
            'android:exported="true" android:label="Settings">\n'
            '\t\t\t<intent-filter>\n'
            '\t\t\t\t<action android:name="android.intent.action.MAIN"/>\n'
            '\t\t\t\t<category android:name="android.intent.category.LAUNCHER"/>\n'
            '\t\t\t</intent-filter>\n'
            '\t\t</activity>\n'
        )
        additions.append("__SETTINGS_ACTIVITY__")
    perm_block = "\n".join(additions).replace("__SETTINGS_ACTIVITY__", settings)
import xml.etree.ElementTree as ET

def edit_manifest():
    tree = ET.parse(MANIFEST)
    root = tree.getroot()
    
    # Add missing permissions
    existing_perms = {p.get('{http://schemas.android.com/apk/res/android}name') for p in root.findall('uses-permission')}
    for p in NEW_PERMS:
        if p not in existing_perms:
            new_perm = ET.Element('uses-permission', {'android:name': p})
            root.insert(0, new_perm)

    # Add SettingsActivity if missing
    if not root.findall(".//activity[@android:name='tech.ula.SettingsActivity']", namespaces={'android': 'http://schemas.android.com/apk/res/android'}):
        app = root.find('application')
        if app is not None:
            activity = ET.SubElement(app, 'activity', {
                'android:name': 'tech.ula.SettingsActivity',
                'android:exported': 'true',
                'android:label': 'Settings'
            })
            intent_filter = ET.SubElement(activity, 'intent-filter')
            ET.SubElement(intent_filter, 'action', {'android:name': 'android.intent.action.MAIN'})
            ET.SubElement(intent_filter, 'category', {'android:name': 'android.intent.category.LAUNCHER'})

    tree.write(MANIFEST, encoding='utf-8', xml_declaration=True)
    print("[edit] manifest updated using XML parser")
    open(MANIFEST, "w", encoding="utf-8").write(txt)
    print(f"[edit] manifest updated: +{len(NEW_PERMS)} perms considered, "
          f"SettingsActivity={'added' if 'SettingsActivity' in txt else 'present'}")

def rebuild():
    env = dict(os.environ)
    env["JAVA_TOOL_OPTIONS"] = (
        "-Djava.security.properties="
        + TC + "/rootfs/usr/lib/jvm/java-17-openjdk-arm64/conf/security/java.security"
    )
    # build with apktool (uses its bundled aapt)
    subprocess.run(["java", "-jar", APKTOOL, "b", "-f", "-o", OUT_APK, DEC],
                   env=env, check=True)
    print(f"[build] unsigned APK -> {OUT_APK}")

def resign():
    env = dict(os.environ)
    env["JAVA_TOOL_OPTIONS"] = (
        "-Djava.security.properties="
        + TC + "/rootfs/usr/lib/jvm/java-17-openjdk-arm64/conf/security/java.security"
    )
    # zipalign-style align is optional; apksigner handles v1+v2
    subprocess.run([
        "java", "-jar",
        TC + "/rootfs/usr/share/java/apksigner.jar",
        "sign", "--ks", KEYSTORE, "--ks-key-alias", "ula",
        "--ks-pass", f"pass:{os.getenv('KS_PASS', 'ula123')}", "--key-pass", f"pass:{os.getenv('KEY_PASS', 'ula123')}",
        "--out", FINAL_APK, OUT_APK,
    ], env=env, check=True)
    print(f"[sign] signed APK -> {FINAL_APK}")

if __name__ == "__main__":
    edit_manifest()
    rebuild()
    resign()
    print("[done] ula_modified_signed.apk ready")
