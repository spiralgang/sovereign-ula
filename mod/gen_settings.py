import xml.etree.ElementTree as ET

# Full settings PreferenceScreen: enumerates every permission capability the app requests,
# plus shared-storage/Downloads access, billing-disabled, signing-cert-required, enable-all-permissions.
settings = '''<?xml version="1.0" encoding="utf-8"?>
<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    android:title="ULA Full Settings">
    <PreferenceCategory android:title="Permissions">
        <SwitchPreference
            android:key="perm_enable_all"
            android:title="Enable ALL requested permissions"
            android:summary="Grant the entire declared permission suite (storage, phone, location, device-admin, accessibility, overlay, install)."
            android:defaultValue="true" />
        <Preference
            android:key="perm_open_settings"
            android:title="Open system App Permissions"
            android:summary="Jump to Android Settings to review/grant every requested permission.">
            <intent android:action="android.settings.APPLICATION_DETAILS_SETTINGS"
                android:data="package:tech.ula" />
        </Preference>
        <Preference
            android:key="perm_all_files"
            android:title="All Files Access (shared storage)"
            android:summary="MANAGE_EXTERNAL_STORAGE: full read/write to shared storage and Downloads.">
            <intent android:action="android.settings.MANAGE_ALL_FILES_ACCESS_PERMISSION"
                android:data="package:tech.ula" />
        </Preference>
        <Preference
            android:key="perm_downloads"
            android:title="Direct access to shared storage Downloads"
            android:summary="READ/WRITE_EXTERNAL_STORAGE + MANAGE_MEDIA: open /Download directly.">
            <intent android:action="android.intent.action.OPEN_DOCUMENT_TREE" />
        </Preference>
        <Preference
            android:key="perm_overlay"
            android:title="Display over other apps"
            android:summary="SYSTEM_ALERT_WINDOW (overlay / edge panel).">
            <intent android:action="android.settings.action.MANAGE_OVERLAY_PERMISSION"
                android:data="package:tech.ula" />
        </Preference>
        <Preference
            android:key="perm_accessibility"
            android:title="Accessibility service"
            android:summary="BIND_ACCESSIBILITY_SERVICE.">
            <intent android:action="android.settings.ACCESSIBILITY_SETTINGS" />
        </Preference>
        <Preference
            android:key="perm_device_admin"
            android:title="Device admin"
            android:summary="BIND_DEVICE_ADMIN.">
            <intent android:action="android.settings.SECURITY_SETTINGS" />
        </Preference>
        <Preference
            android:key="perm_install"
            android:title="Install unknown apps"
            android:summary="REQUEST_INSTALL_PACKAGES.">
            <intent android:action="android.settings.MANAGE_UNKNOWN_APP_SOURCES"
                android:data="package:tech.ula" />
        </Preference>
        <SwitchPreference
            android:key="perm_location"
            android:title="Location (coarse + fine)"
            android:summary="ACCESS_COARSE_LOCATION / ACCESS_FINE_LOCATION." />
        <SwitchPreference
            android:key="perm_camera_mic"
            android:title="Camera + Microphone"
            android:summary="CAMERA / RECORD_AUDIO." />
        <SwitchPreference
            android:key="perm_contacts"
            android:title="Contacts / Calendar / SMS"
            android:summary="READ_CONTACTS, READ_CALENDAR, READ_SMS, etc." />
        <SwitchPreference
            android:key="perm_phone"
            android:title="Phone / Calls"
            android:summary="CALL_PHONE, READ_PHONE_STATE, etc." />
        <SwitchPreference
            android:key="perm_bluetooth"
            android:title="Bluetooth"
            android:summary="BLUETOOTH_CONNECT / BLUETOOTH_SCAN." />
        <SwitchPreference
            android:key="perm_secure_settings"
            android:title="Write secure settings"
            android:summary="WRITE_SECURE_SETTINGS / WRITE_SETTINGS." />
    </PreferenceCategory>

    <PreferenceCategory android:title="Storage &amp; Files">
        <Preference
            android:key="open_downloads"
            android:title="Open Downloads (shared storage)"
            android:summary="Launch the system Downloads / document tree root.">
            <intent android:action="android.intent.action.OPEN_DOCUMENT_TREE" />
        </Preference>
        <SwitchPreference
            android:key="manage_media"
            android:title="Manage media (MANAGE_MEDIA)"
            android:summary="Broad access to shared media collections." />
    </PreferenceCategory>

    <PreferenceCategory android:title="Billing">
        <SwitchPreference
            android:key="billing_disabled"
            android:title="Paid billing: DISABLED"
            android:summary="In-app purchase / paid billing is turned off. App is free / ad-free of billing."
            android:defaultValue="true" />
        <Preference
            android:key="billing_status"
            android:title="Billing state"
            android:summary="billingDisabled=true (mandatory off)" />
    </PreferenceCategory>

    <PreferenceCategory android:title="Signing &amp; Integrity">
        <SwitchPreference
            android:key="signing_cert_required"
            android:title="Signing certificate mandatory"
            android:summary="App refuses to run / update unless signed by the required release certificate."
            android:defaultValue="true" />
        <Preference
            android:key="view_cert"
            android:title="View signing certificate"
            android:summary="Show the mandatory signing certificate fingerprint (CERT.RSA)." />
    </PreferenceCategory>

    <PreferenceCategory android:title="Edge Panel">
        <SwitchPreference
            android:key="edge_panel_enabled"
            android:title="Enable edge panel"
            android:summary="Show the ULA settings edge panel overlay (requires SYSTEM_ALERT_WINDOW)."
            android:defaultValue="true" />
        <ListPreference
            android:key="edge_panel_side"
            android:title="Edge panel side"
            android:summary="Which screen edge hosts the panel."
            android:entries="@android:array/phoneEmailTypes"
            android:entryValues="left:right" />
    </PreferenceCategory>
</PreferenceScreen>
'''

open("/home/spiralgang/toolchain/work/preferences_full.xml","w",encoding="utf-8").write(settings)
try:
    ET.fromstring(settings); print("SETTINGS WELL-FORMED: OK")
except ET.ParseError as e:
    print("SETTINGS PARSE ERROR:", e)
print("settings bytes:", len(settings))
