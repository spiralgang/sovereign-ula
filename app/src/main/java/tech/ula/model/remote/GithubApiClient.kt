package tech.ula.model.remote

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import tech.ula.utils.Logger
import tech.ula.utils.SentryLogger
import tech.ula.utils.UlaFiles
import java.io.IOException
import java.net.UnknownHostException

class UrlProvider {
    fun getBaseUrl(): String {
        return "https://api.github.com/"
    }
}

class GithubApiClient(
    private val ulaFiles: UlaFiles,
    private val urlProvider: UrlProvider = UrlProvider(),
    private val logger: Logger = SentryLogger()
) {
    private val client = OkHttpClient()
    private val latestResults: HashMap<String, ReleasesResponse?> = hashMapOf()

    // Distro assets are published by distro-deploy-listener.yml as releases on
    // spiralgang/sovereign-ula TAGGED with the distro name (ubuntu | debian |
    // arch), NOT as "latest". "latest" is whatever release was created most
    // recently — which is the signed APK release from build.yml, containing no
    // distro assets. Using "latest" made every asset lookup fail (NPE crash on
    // session start and a bogus "network required" error even with
    // connectivity), so we query the distro-named tag directly.
    private fun getReleaseToUseForRepo(repo: String): String {
        return "tags/$repo"
    }

    @Throws(IOException::class)
    suspend fun getAssetsListDownloadUrl(repo: String): String = withContext(Dispatchers.IO) {
        val result = latestResults[repo] ?: queryLatestRelease(repo)
        val assetName = "${ulaFiles.getArchType()}-assets.txt"

        val asset = result.assets.find { it.name == assetName }
                ?: throw IOException("Release '${result.tag}' has no asset '$assetName'")
        return@withContext asset.downloadUrl
    }

    @Throws(IOException::class)
    suspend fun getLatestReleaseVersion(repo: String): String = withContext(Dispatchers.IO) {
        val result = latestResults[repo] ?: queryLatestRelease(repo)

        return@withContext result.tag
    }

    @Throws(IOException::class)
    suspend fun getAssetEndpoint(assetType: String, repo: String): String = withContext(Dispatchers.IO) {
        val result = latestResults[repo] ?: queryLatestRelease(repo)
        val assetName = "${ulaFiles.getArchType()}-$assetType"

        val asset = result.assets.find { it.name == assetName }
                ?: throw IOException("Release '${result.tag}' has no asset '$assetName'")
        return@withContext asset.downloadUrl
    }

    // Query latest release data and memoize results.
    @Throws(IOException::class, UnknownHostException::class)
    private suspend fun queryLatestRelease(repo: String): ReleasesResponse = withContext(Dispatchers.IO) {
        val releaseToUse = getReleaseToUseForRepo(repo)
        val base = urlProvider.getBaseUrl()
        // Distro rootfs/assets releases are self-hosted: distro-deploy-listener.yml
        // publishes them to spiralgang/sovereign-ula (tag = distro name).
        val url = base + "repos/spiralgang/sovereign-ula/releases/$releaseToUse"
        val moshi = Moshi.Builder().build()
        val adapter = moshi.adapter(ReleasesResponse::class.java)
        val request = Request.Builder()
                .url(url)
                .build()
        val response = try {
            client.newCall(request).execute()
        } catch (err: UnknownHostException) {
            logger.addExceptionBreadcrumb(err)
            throw err
        }
        if (!response.isSuccessful) {
            val err = IOException("Unexpected code: $response")
            logger.addExceptionBreadcrumb(err)
            throw err
        }

        val result = adapter.fromJson(response.body()!!.source())!!
        latestResults[repo] = result
        return@withContext result
    }

    @JsonClass(generateAdapter = true)
    internal data class ReleasesResponse(
        val url: String,
        val name: String,
        @Json(name = "tag_name") val tag: String,
        val assets: List<GithubAsset>
    )

    @JsonClass(generateAdapter = true)
    internal data class GithubAsset(
        val url: String,
        val name: String,
        @Json(name = "browser_download_url") val downloadUrl: String
    )
}