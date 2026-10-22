package tech.ula.ui

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.Drawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import tech.ula.R
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.Preference
import tech.ula.utils.ProotDebugLogger
import tech.ula.utils.UlaFiles
import tech.ula.utils.defaultSharedPreferences

class SettingsFragment : PreferenceFragmentCompat() {

    private val prootDebugLogger by lazy {
        val ulaFiles = UlaFiles(activity!!, activity!!.applicationInfo.nativeLibraryDir)
        ProotDebugLogger(activity!!.defaultSharedPreferences, ulaFiles)
    }

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        addPreferencesFromResource(R.xml.preferences)

        val deleteFilePreference: Preference = findPreference("pref_proot_delete_debug_file")!!
        deleteFilePreference.setOnPreferenceClickListener {
            prootDebugLogger.deleteLogs()
            true
        }

        val clearAutoStartPreference: Preference = findPreference("pref_clear_auto_start")!!
        clearAutoStartPreference.setOnPreferenceClickListener {
            val prefs = activity!!.getSharedPreferences("apps", Context.MODE_PRIVATE)
            with(prefs.edit()) {
                remove("AutoApp")
                apply()
                true
            }
        }

        wireSovereignPreferences()
    }

    private fun wireSovereignPreferences() {
        val pkg = activity!!.packageName

        findPreference<Preference>("sov_enable_all_perms")?.setOnPreferenceClickListener {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:$pkg")))
            true
        }

        findPreference<Preference>("sov_open_downloads")?.setOnPreferenceClickListener {
            val i = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            startActivity(i)
            true
        }

        findPreference<Preference>("sov_manage_storage")?.setOnPreferenceClickListener {
            if (Build.VERSION.SDK_INT >= 30) {
                // API 30+ dedicated screen (constant not present on SDK 29)
                startActivity(Intent("android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION",
                        Uri.parse("package:$pkg")))
            } else {
                Toast.makeText(activity, "Not required below Android 11", Toast.LENGTH_SHORT).show()
            }
            true
        }

        findPreference<Preference>("sov_overlay_perm")?.setOnPreferenceClickListener {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$pkg")))
            }
            true
        }

        findPreference<Preference>("sov_edge_panel_enabled")?.setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            val svc = Intent(activity, EdgePanelService::class.java)
            if (enabled) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    activity!!.startForegroundService(svc)
                } else {
                    activity!!.startService(svc)
                }
            } else {
                activity!!.stopService(svc)
            }
            true
        }

        findPreference<Preference>("sov_accessibility_enabled")?.setOnPreferenceClickListener {
            // Deep-link into Android's accessibility settings so the user can
            // toggle the Sovereign accessibility service on.
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            true
        }
    }

    override fun setDivider(divider: Drawable?) {
        super.setDivider(ColorDrawable(Color.TRANSPARENT))
    }

    override fun setDividerHeight(height: Int) {
        super.setDividerHeight(0)
    }
}