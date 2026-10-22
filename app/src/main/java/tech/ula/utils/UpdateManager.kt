package tech.ula.utils

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class UpdateManager(private val context: Context) {
    private val TAG = "UpdateManager"
    private val GITHUB_RELEASES_URL = "https://api.github.com/repos/spiralgang/sovereign-ula/releases/latest"

    data class ReleaseInfo(val tagName: String, val downloadUrl: String, val body: String)

    suspend fun checkLatestRelease(currentVersion: String): ReleaseInfo? = withContext(Dispatchers.IO) {
        try {
            val url = URL(GITHUB_RELEASES_URL)
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.setRequestProperty("User-Agent", "SovereignULA-UpdateManager")
            
            if (connection.responseCode == 200) {
                val text = connection.inputStream.bufferedReader().use { it.readText() }
                val json = JSONObject(text)
                val tagName = json.getString("tag_name")
                val body = json.getString("body")
                
                // Find the APK download URL in the assets
                val assets = json.getJSONArray("assets")
                var downloadUrl = ""
                for (i in 0 until assets.length()) {
                    val asset = assets.getJSONObject(i)
                    if (asset.getString("name").endsWith(".apk")) {
                        downloadUrl = asset.getString("browser_download_url")
                        break
                    }
                }
                
                if (tagName != currentVersion) {
                    return@withContext ReleaseInfo(tagName, downloadUrl, body)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to check for updates: ${e.message}")
        }
        return@withContext null
    }
}
