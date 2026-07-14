package tech.ula.ui

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.net.Uri
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import tech.ula.R

/**
 * Foreground service that draws the Sovereign settings edge-panel overlay.
 * Requires SYSTEM_ALERT_WINDOW (granted via the settings screen).
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
                    .setContentTitle("Sovereign Edge Panel")
                    .setContentText("Settings edge panel is active")
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                    .setContentTitle("Sovereign Edge Panel")
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
                (220 * resources.displayMetrics.density).toInt(),
                WindowManager.LayoutParams.WRAP_CONTENT,
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT)
        params.gravity = Gravity.END or Gravity.CENTER_VERTICAL
        panel = LayoutInflater.from(this).inflate(R.layout.edge_panel, null)
        wireButtons(panel!!)
        windowManager?.addView(panel, params)
    }

    private fun wireButtons(root: View) {
        val pkg = packageName
        root.findViewById<Button>(R.id.btn_open_settings)?.setOnClickListener {
            val i = Intent(this, MainActivity::class.java)
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            i.putExtra("navigate_to", "settings_fragment")
            startActivity(i)
            hidePanel()
        }
        root.findViewById<Button>(R.id.btn_enable_all_perms)?.setOnClickListener {
            val i = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$pkg"))
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(i)
        }
        root.findViewById<Button>(R.id.btn_open_downloads)?.setOnClickListener {
            val i = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(i)
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
