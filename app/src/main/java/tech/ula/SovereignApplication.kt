package tech.ula

import android.app.Application
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.os.Build
import android.util.Log
import java.security.MessageDigest

/**
 * Enforces that the app is signed with the Sovereign release certificate.
 * Tampered / re-signed builds refuse to start. Disabled for debug builds so
 * local/CI debug installs still run.
 */
class SovereignApplication : Application() {

    // SHA-256 of the mandated release signing certificate (colons stripped, upper-case).
    private val REQUIRED_CERT_SHA256 =
        "A813923E99B09FAF6558DB5B5FEC1FFBFF0250791BC05A79F58470077D89201F"

    override fun onCreate() {
        super.onCreate()
        if (!BuildConfig.DEBUG && !isSignedBySovereignCert()) {
            Log.e("Sovereign", "Unauthorized build: signing certificate does not match. Refusing to run.")
            android.os.Process.killProcess(android.os.Process.myPid())
            System.exit(1)
        }
    }

    private fun isSignedBySovereignCert(): Boolean {
        return try {
            val pm = packageManager
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                PackageManager.GET_SIGNING_CERTIFICATES
            } else {
                @Suppress("DEPRECATION") PackageManager.GET_SIGNATURES
            }
            val pi: PackageInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                pm.getPackageInfo(packageName, flags)
            } else {
                @Suppress("DEPRECATION") pm.getPackageInfo(packageName, flags)
            }
            val sigs: Array<out Signature>? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                pi.signingInfo?.apkContentsSigners
            } else {
                @Suppress("DEPRECATION") pi.signatures
            }
            sigs?.any { sha256(it.toByteArray()) == REQUIRED_CERT_SHA256 } ?: false
        } catch (e: Exception) {
            Log.e("Sovereign", "cert check failed", e)
            false
        }
    }

    private fun sha256(data: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        return md.digest(data).joinToString("") { "%02X".format(it) }
    }
}
