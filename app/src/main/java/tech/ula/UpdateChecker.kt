package tech.ula

import android.content.Context
import android.util.Log
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.Request
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class UpdateChecker(private val context: Context) {
    private val client = OkHttpClient()
    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val releaseAdapter = moshi.adapter(ReleaseResponse::class.java)

    data class ReleaseResponse(val tag_name: String)

    suspend fun checkForUpdate(currentVersion: String): String? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("https://api.github.com/repos/spiralgang/sovereign-ula/releases/latest")
                .build()
            
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@withContext null
                
                val body = response.body?.string() ?: return@withContext null
                val latestRelease = releaseAdapter.fromJson(body)
                
                val latestVersion = latestRelease?.tag_name ?: return@withContext null
                if (latestVersion != currentVersion) {
                    return@withContext latestVersion
                }
            }
        } catch (e: Exception) {
            Log.e("UpdateChecker", "Error checking for updates", e)
        }
        null
    }
}
