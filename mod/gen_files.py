import xml.etree.ElementTree as ET

# Verified clean, unique permission set extracted earlier (android + vendor),
# excluding the bogus non-permission entries (intent actions, categories, services).
PERMS = [
"android.permission.ACCESS_ADSERVICES_AD_ID","android.permission.ACCESS_ADSERVICES_ATTRIBUTION","android.permission.ACCESS_ADSERVICES_TOPICS",
"android.permission.ACCESS_COARSE_LOCATION","android.permission.ACCESS_FINE_LOCATION","android.permission.ACCESS_KEYGUARD_SECURE_STORAGE",
"android.permission.ACCESS_NETWORK_STATE","android.permission.ACCESS_NOTIFICATION_POLICY","android.permission.ACCESS_WIFI_STATE",
"android.permission.ADD_VOICEMAIL","android.permission.ANSWER_PHONE_CALLS","android.permission.ASEC_ACCESS","android.permission.ASEC_CREATE",
"android.permission.ASEC_DESTROY","android.permission.ASEC_MOUNT_UNMOUNT","android.permission.AUTHENTICATE_ACCOUNTS","android.permission.BATTERY_STATS",
"android.permission.BIND_ACCESSIBILITY_SERVICE","android.permission.BIND_APPWIDGET","android.permission.BIND_CALL_REDIRECTION_SERVICE",
"android.permission.BIND_CHOOSER_TARGET_SERVICE","android.permission.BIND_CONDITION_PROVIDER_SERVICE","android.permission.BIND_DEVICE_ADMIN",
"android.permission.BIND_DREAM_SERVICE","android.permission.BIND_INCALL_SERVICE","android.permission.BIND_INPUT_METHOD","android.permission.BIND_JOB_SERVICE",
"android.permission.BIND_KEYGUARD","android.permission.BIND_MIDI_DEVICE_SERVICE","android.permission.BIND_NFC_SERVICE",
"android.permission.BIND_NOTIFICATION_LISTENER_SERVICE","android.permission.BIND_PRINT_SERVICE","android.permission.BIND_QUICK_SETTINGS_TILE",
"android.permission.BIND_REMOTEVIEWS","android.permission.BIND_ROLE_SERVICE","android.permission.BIND_RUNNING_SERVICE",
"android.permission.BIND_TELECOM_CONNECTION_SERVICE","android.permission.BIND_TEXT_SERVICE","android.permission.BIND_TRUST_AGENT",
"android.permission.BIND_TV_INPUT","android.permission.BIND_VOICE_INTERACTION","android.permission.BIND_VPN_SERVICE","android.permission.BIND_WALLPAPER",
"android.permission.BLUETOOTH","android.permission.BLUETOOTH_ADMIN","android.permission.BLUETOOTH_CONNECT","android.permission.BLUETOOTH_SCAN",
"android.permission.BROADCAST_CLOSE_SYSTEM_DIALOGS","android.permission.BROADCAST_PACKAGE_REMOVED","android.permission.BROADCAST_SMS",
"android.permission.BROADCAST_STICKY","android.permission.BROADCAST_WAP_PUSH","android.permission.CALL_PHONE","android.permission.CALL_PRIVILEGED",
"android.permission.CAMERA","android.permission.CAPTURE_AUDIO_OUTPUT","android.permission.CAPTURE_SECURE_VIDEO_OUTPUT","android.permission.CAPTURE_VIDEO_OUTPUT",
"android.permission.CERTIFICATE_ACCESS","android.permission.CHANGE_COMPONENT_ENABLED_STATE","android.permission.CHANGE_CONFIGURATION",
"android.permission.CHANGE_NETWORK_STATE","android.permission.CHANGE_WIFI_MULTICAST_STATE","android.permission.CHANGE_WIFI_STATE",
"android.permission.CLEAR_APP_CACHE","android.permission.CLEAR_APP_USER_DATA","android.permission.CONTROL_LOCATION_UPDATES","android.permission.CREATE_MOCK_LOCATION",
"android.permission.CRYPT_KERNEL","android.permission.DELETE_CACHE_FILES","android.permission.DELETE_PACKAGES","android.permission.DEVICE_POWER",
"android.permission.DIAGNOSTIC","android.permission.DISABLE_KEYGUARD","android.permission.DUMP","android.permission.DUMP_APP","android.permission.EXPAND_STATUS_BAR",
"android.permission.FACTORY_TEST","android.permission.FLASHLIGHT","android.permission.FORCE_BACK","android.permission.FORCE_STOP_PACKAGES","android.permission.FOREGROUND_SERVICE",
"android.permission.FOREGROUND_SERVICE_CAMERA","android.permission.FOREGROUND_SERVICE_DATA_SYNC","android.permission.FOREGROUND_SERVICE_LOCATION",
"android.permission.FOREGROUND_SERVICE_MICROPHONE","android.permission.FOREGROUND_SERVICE_SPEAKERPHONE","android.permission.GET_ACCOUNTS",
"android.permission.GET_ACCOUNTS_PRIVILEGED","android.permission.GET_APP_OPS_STATS","android.permission.GET_PACKAGE_SIZE","android.permission.GET_TASKS",
"android.permission.GET_TOP_ACTIVITY_INFO","android.permission.GLOBAL_SEARCH","android.permission.GRANT_RUNTIME_PERMISSIONS","android.permission.GRANT_REVOKE_PERMISSIONS",
"android.permission.HARDWARE_CONTROL","android.permission.HARDWARE_TEST","android.permission.HDMI_CEC","android.permission.HEADSET_PLUG",
"android.permission.INSTALL_GRANT_RUNTIME_PERMISSIONS","android.permission.INSTALL_LOCATION_PROVIDER","android.permission.INSTALL_PACKAGES","android.permission.INSTALL_SHORTCUT",
"android.permission.INSTANT_APP_FOREGROUND_SERVICE","android.permission.INTERACT_ACROSS_USERS","android.permission.INTERACT_ACROSS_USERS_FULL","android.permission.INTERNET",
"android.permission.INVOKE_CARRIER_SETUP","android.permission.KILL_BACKGROUND_PROCESSES","android.permission.LOCATION_HARDWARE","android.permission.LOOP_RADIO",
"android.permission.MANAGE_ACCOUNTS","android.permission.MANAGE_ACTIVITY_STACKS","android.permission.MANAGE_APP_TOKENS","android.permission.MANAGE_CALENDAR",
"android.permission.MANAGE_CAMERA","android.permission.MANAGE_DEVICE_ADMINS","android.permission.MANAGE_DEVICE_POLICY_DEBUGGING_FEATURES","android.permission.MANAGE_DOCUMENTS",
"android.permission.MANAGE_EXTERNAL_STORAGE","android.permission.MANAGE_MEDIA","android.permission.MANAGE_NOTIFICATIONS","android.permission.MANAGE_PROFILE_AND_DEVICE_OWNERS",
"android.permission.MANAGE_SOUND_SETTINGS","android.permission.MANAGE_USB","android.permission.MANAGE_VOICE_KEYPHRASES","android.permission.MASTER_CLEAR",
"android.permission.MEDIA_CONTENT_CONTROL","android.permission.MODIFY_AUDIO_SETTINGS","android.permission.MODIFY_PHONE_STATE","android.permission.MOUNT_FORMAT_FILESYSTEMS",
"android.permission.MOUNT_UNMOUNT_FILESYSTEMS","android.permission.MOVE_PACKAGE","android.permission.NET_ADMIN","android.permission.NET_TUNNELING","android.permission.NFC",
"android.permission.NFC_HANDOVER","android.permission.NFC_PREFERRED_PAYMENT_INFO","android.permission.OBSERVE_GRANT_REVOKE_PERMISSIONS","android.permission.OVERRIDE_WIFI_CONFIG",
"android.permission.PERSISTENT_ACTIVITY","android.permission.PROCESS_OUTGOING_CALLS","android.permission.PROVIDE_TRUST_AGENT","android.permission.QUERY_ALL_PACKAGES",
"android.permission.READ_CALENDAR","android.permission.READ_CALL_LOG","android.permission.READ_CONTACTS","android.permission.READ_DEVICE_CONFIG","android.permission.READ_EXTERNAL_STORAGE",
"android.permission.READ_FRAME_BUFFER","android.permission.READ_INPUT_STATE","android.permission.READ_LOGS","android.permission.READ_PHONE_NUMBERS",
"android.permission.READ_PRIVILEGED_PHONE_STATE","android.permission.READ_SMS","android.permission.READ_SOCIAL_STREAM","android.permission.READ_SYNC_SETTINGS",
"android.permission.READ_SYNC_STATS","android.permission.READ_USER_DICTIONARY","android.permission.READ_VOICEMAIL","android.permission.REBOOT","android.permission.RECORD_AUDIO",
"android.permission.REORDER_TASKS","android.permission.REQUEST_COMPANION_PROFILE","android.permission.REQUEST_COMPANION_RUN_IN_BACKGROUND","android.permission.REQUEST_DELETE_PACKAGES",
"android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS","android.permission.REQUEST_INSTALL_PACKAGES","android.permission.REQUEST_OBSERVE_GRANT_REVOKE_PERMISSIONS",
"android.permission.REQUEST_PASSWORD","android.permission.RESTART_PACKAGES","android.permission.RESTRICTED_SETTINGS","android.permission.SCHEDULE_EXACT_ALARM",
"android.permission.SEND_RESPOND_VIA_MESSAGE","android.permission.SEND_SMS","android.permission.SET_ALARM","android.permission.SET_ALWAYS_FINISH","android.permission.SET_ANIMATION_SCALE",
"android.permission.SET_DEBUG_APP","android.permission.SET_ORIENTATION","android.permission.SET_POINTER_SPEED","android.permission.SET_PREFERRED_APPLICATIONS",
"android.permission.SET_PROCESS_LIMIT","android.permission.SET_SCREEN_COMPATIBILITY","android.permission.SET_TIME","android.permission.SET_TIME_ZONE","android.permission.SET_WALLPAPER",
"android.permission.SET_WALLPAPER_HINTS","android.permission.SIGNAL_PERSISTENT_PROCESSES","android.permission.SMS_FINANCIAL_TRANSACTIONS","android.permission.START_ANY_ACTIVITY",
"android.permission.START_TASKS_FROM_RECENTS","android.permission.STATUS_BAR","android.permission.STATUS_BAR_SERVICE","android.permission.STOP_APP_SWITCHES",
"android.permission.SUBSCRIBED_FEEDS_ACCESS","android.permission.SURFACE_FLINGER","android.permission.SYSTEM_ALERT_WINDOW","android.permission.SYSTEM_OVERLAY_WINDOW",
"android.permission.TEMPORARY_ENABLE_ACCESSIBILITY","android.permission.TRANSMIT_IR","android.permission.TUNNEL_MODE","android.permission.UPDATE_DEVICE_STATS",
"android.permission.UPDATE_PACKAGES_WITHOUT_USER_ACTION","android.permission.USE_BIOMETRIC","android.permission.USE_CREDENTIALS","android.permission.USE_FINGERPRINT",
"android.permission.USE_FULL_SCREEN_INTENT","android.permission.USE_SIP","android.permission.USE_TUNNEL_MODE","android.permission.VIBRATE","android.permission.VOICEMAIL",
"android.permission.VR_LISTENER_SERVICE","android.permission.WAKE_LOCK","android.permission.WRITE_APN_SETTINGS","android.permission.WRITE_CALENDAR","android.permission.WRITE_CALL_LOG",
"android.permission.WRITE_CONTACTS","android.permission.WRITE_DREAM_STATE","android.permission.WRITE_EXTERNAL_STORAGE","android.permission.WRITE_GSERVICES","android.permission.WRITE_MEDIA_STORAGE",
"android.permission.WRITE_OWNER_DATA","android.permission.WRITE_SECURE_SETTINGS","android.permission.WRITE_SETTINGS","android.permission.WRITE_SMS","android.permission.WRITE_SOCIAL_STREAM",
"android.permission.WRITE_SYNC_SETTINGS","android.permission.WRITE_USER_DICTIONARY",
"com.samsung.android.knox.permission.KNOX_APP_MGMT","com.samsung.android.knox.permission.KNOX_APP_SEPARATION","com.samsung.android.knox.permission.KNOX_CONTAINER",
"com.samsung.android.knox.permission.KNOX_ENTERPRISE_DEVICE_ADMIN","com.samsung.android.knox.permission.KNOX_HW_CONTROL","com.samsung.android.knox.permission.KNOX_KIOSK_MODE",
"com.samsung.android.knox.permission.KNOX_LOCATION","com.samsung.android.knox.permission.KNOX_RESTRICTION_MGMT","com.samsung.android.knox.permission.KNOX_SECURITY",
"com.samsung.android.appseparation.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION","com.samsung.android.carrier.permission.UPDATE_CARRIER","com.samsung.android.fotaclient.permission.FOTA",
"com.samsung.android.kgclient.permission.ACCESS","com.samsung.android.launcher.permission.WRITE_SETTINGS","com.samsung.android.sdm.config.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
"com.samsung.android.sdm.config.permission.RECEIVE_CONFIG_CHANGED","com.samsung.permission.READ_DW_DATA","com.sec.android.EXCEPTION_AUTORUN_DEFAULT_OFF",
"com.sec.android.app.SecSetupWizard.permission.SHOW_SETUP_WIZARD","com.sec.android.fido.uaf.asm.permissions.FIDO_UAF_ASM","com.sec.android.fido.uaf.asm.permissions.MIGRATION",
"com.sec.android.fido.uaf.client.permissions.FIDO_UAF_CLIENT_PRIVILEGED","com.sec.android.provider.badge.permission.READ","com.sec.android.provider.badge.permission.WRITE",
"com.sec.mhs.smarttethering.RECEIVE_SMARTTETHERING","com.sec.permission.preconfig",
"com.sec.spp.permission.TOKEN_cc1de5b009a732084879b12fab52f456bc6eac0cc0bdc5d9330ec8034242c9ec9a55ec20b7ea6b631632fc9b0e8770b13026dc2612dae8ca3593134ceef544677d1dba3b5606cccafd74eb7a152dc8c5c0bfa6f4ea26d022046d00276d1bb953a9c817172f8415e88dc0af6fa098c2b80b4394709224ad94c06059802835d641",
"moe.shizuku.manager.permission.MANAGER","com.verizon.api.ACCESS","com.verizon.mips.services.COMPONENT_STATUS","com.verizon.mips.services.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
"com.verizon.services.eps.EPS_SWITCH_ENV","com.verizon.svcs.fdo.FA_SWITCH_ENV","com.verizon.vzwavs.mvs.permission.WRITE","com.verizon.vzwavs.permission.READ","com.vzw.APNPERMISSION",
"com.vzw.services.lc.SWITCH_ENV","com.wallet.crypto.trustapp.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION","net.kollnig.missioncontrol.github.permission.ADMIN","org.fidoalliance.uaf.permissions.FIDO_CLIENT",
]

# De-dupe preserving order
seen=set(); perms=[p for p in PERMS if not (p in seen or seen.add(p))]
print("TOTAL PERMS:", len(perms))

def perm_block(perms):
    return "\n".join(f'\t<uses-permission android:name="{n}" />' for n in perms)

app_block = '''\t<application android:theme="@7F130007" android:label="@7F12002D" android:icon="@7F0E0000" android:allowBackup="true" android:supportsRtl="true" android:banner="@7F08005E" android:extractNativeLibs="true" android:fullBackupContent="@7F150000" android:roundIcon="@7F0E0002" android:appComponentFactory="androidx.core.app.CoreComponentFactory">
\t\t<activity android:name="tech.ula.MainActivity" android:launchMode="2">
\t\t\t<intent-filter>
\t\t\t\t<action android:name="android.intent.action.MAIN" />
\t\t\t\t<action android:name="android.intent.action.VIEW" />
\t\t\t\t<category android:name="android.intent.category.DEFAULT" />
\t\t\t\t<category android:name="android.intent.category.LAUNCHER" />
\t\t\t</intent-filter>
\t\t</activity>
\t\t<service android:name="tech.ula.ServerService" android:stopWithTask="true">
\t\t</service>
\t\t<provider android:name="tech.ula.provider.UlaDocProvider" android:permission="android.permission.MANAGE_DOCUMENTS" android:exported="true" android:authorities="tech.ula.documents" android:grantUriPermissions="true">
\t\t\t<intent-filter>
\t\t\t\t<action android:name="android.content.action.DOCUMENTS_PROVIDER" />
\t\t\t</intent-filter>
\t\t</provider>
\t\t<meta-data android:name="android.max_aspect" android:value="10.0" />
\t\t<activity android:name="com.termux.app.TermuxActivity" android:launchMode="3" android:configChanges="0x000004B0" android:windowSoftInputMode="0x00000015" android:resizeableActivity="true">
\t\t\t<intent-filter>
\t\t\t\t<action android:name="android.intent.action.VIEW" />
\t\t\t\t<category android:name="android.intent.category.DEFAULT" />
\t\t\t\t<category android:name="android.intent.category.BROWSABLE" />
\t\t\t\t<data android:scheme="ssh" />
\t\t\t</intent-filter>
\t\t\t<meta-data android:name="android.app.shortcuts" android:resource="@7F150002" />
\t\t</activity>
\t\t<service android:name="com.termux.app.TermuxService" android:exported="true">
\t\t</service>
\t\t<meta-data android:name="com.sec.android.support.multiwindow" android:value="true" />
\t\t<service android:name="androidx.room.MultiInstanceInvalidationService" android:exported="true">
\t\t</service>
\t\t<provider android:name="androidx.lifecycle.ProcessLifecycleOwnerInitializer" android:exported="true" android:multiprocess="true" android:authorities="tech.ula.lifecycle-process">
\t\t</provider>
\t\t<!-- Full settings + edge-panel entry: alias into MainActivity so the settings screen is launchable without new code -->
\t\t<activity-alias android:name="tech.ula.SettingsEdgePanel" android:enabled="true" android:exported="true" android:targetActivity="tech.ula.MainActivity" android:label="ULA Settings">
\t\t\t<intent-filter>
\t\t\t\t<action android:name="tech.ula.action.OPEN_SETTINGS" />
\t\t\t\t<category android:name="android.intent.category.DEFAULT" />
\t\t\t</intent-filter>
\t\t</activity-alias>
\t</application>'''

manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
 android:versionCode="326557" android:versionName="2.5.14" android:installLocation="1" android:compileSdkVersion="29" android:compileSdkVersionCodename="10" package="tech.ula" platformBuildVersionCode="29" platformBuildVersionName="10">
\t<uses-sdk android:minSdkVersion="21" android:targetSdkVersion="29">
\t</uses-sdk>
\t<!-- ===== Full suite of every permission the app requests (clean, schema-valid) ===== -->
{perm_block(perms)}
{app_block}
</manifest>
'''
open("/home/spiralgang/toolchain/work/AndroidManifest.clean.xml","w",encoding="utf-8").write(manifest)
try:
    ET.fromstring(manifest); print("MANIFEST WELL-FORMED: OK")
except ET.ParseError as e:
    print("MANIFEST PARSE ERROR:", e)
print("manifest bytes:", len(manifest))
