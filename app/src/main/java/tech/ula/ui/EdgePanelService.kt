package tech.ula.ui

import android.accessibilityservice.AccessibilityService
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import tech.ula.R
import tech.ula.MainActivity

/**
 * Foreground service that draws the Sovereign settings edge-panel overlay in the
 * Samsung swipe-out style: a slim handle on the right screen edge that expands
 * into the full settings panel when tapped. Requires SYSTEM_ALERT_WINDOW.
 */
class EdgePanelService : Service() {

    private val channelId = "sovereign_edge_panel"
    private var windowManager: WindowManager? = null
    private var panel: View? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, buildNotification())
        showPanel()
        return START_STICKY
    }

    private fun buildNotification(): Notification {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(channelId, "Edge Panel", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
            Notification.Builder(this, channelId)
                    .setContentTitle("SOVEREIGN-ULA Edge Panel")
                    .setContentText("Settings edge panel is active")
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                    .setContentTitle("SOVEREIGN-ULA Edge Panel")
                    .setContentText("Settings edge panel is active")
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .build()
        }
    }

    private fun showPanel() {
        if (panel != null) return
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else
            @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE
        val params = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT)
        params.gravity = Gravity.END or Gravity.CENTER_VERTICAL
        panel = LayoutInflater.from(this).inflate(R.layout.edge_panel, null)
        wirePanel(panel!!)
        windowManager?.addView(panel, params)
    }

    private fun wirePanel(root: View) {
        val pkg = packageName
        val handle = root.findViewById<View>(R.id.edge_handle)
        val expanded = root.findViewById<View>(R.id.edge_panel_expanded)

        // Swipe-out style: tap the handle to expand/collapse the settings panel.
        fun toggle() {
            expanded.visibility = if (expanded.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }
        handle.setOnClickListener { toggle() }

        root.findViewById<Button>(R.id.btn_open_settings)?.setOnClickListener {
            val i = Intent(this, MainActivity::class.java)
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            i.putExtra("navigate_to", "settings_fragment")
            startActivity(i)
            hidePanel()
        }
        root.findViewById<Button>(R.id.btn_enable_all_perms)?.setOnClickListener {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        root.findViewById<Button>(R.id.btn_manage_storage)?.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 30) {
                startActivity(Intent("android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION",
                        Uri.parse("package:$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        }
        root.findViewById<Button>(R.id.btn_overlay)?.setOnClickListener {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        root.findViewById<Button>(R.id.btn_accessibility)?.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        root.findViewById<Button>(R.id.btn_open_downloads)?.setOnClickListener {
            startActivity(Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        root.findViewById<Button>(R.id.btn_collapse)?.setOnClickListener {
            expanded.visibility = View.GONE
        }
    }

    private fun hidePanel() {
        panel?.let { windowManager?.removeView(it) }
        panel = null
    }

    override fun onDestroy() {
        hidePanel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

/**
 * Sovereign accessibility service. Registered so the app can offer a real
 * Accessibility toggle in settings / the edge panel. The service itself is a
 * minimal stub (no event interception) — it exists to satisfy the OS
 * accessibility contract and to let users grant the capability.
 */
class SovereignAccessibilityService : AccessibilityService() {
    override fun onAccessibilityEvent(event: android.view.accessibility.AccessibilityEvent?) = Unit
    override fun onInterrupt() = Unit
}
