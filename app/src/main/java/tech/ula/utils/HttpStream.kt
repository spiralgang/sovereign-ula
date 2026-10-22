package tech.ula.utils

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.UnknownHostException

class HttpStream {
    // Attempts -> exponential backoff (1s,2s,4s)
    @Throws(IOException::class)
    fun fromUrl(urlStr: String, attempts: Int = 3): InputStream {
        var lastEx: IOException? = null
        var attemptDelay = 1000L
        var currentUrl = urlStr
        for (attempt in 1..attempts) {
            try {
                val url = URL(currentUrl)
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 15_000
                conn.readTimeout = 60_000
                conn.instanceFollowRedirects = false
                conn.setRequestProperty("User-Agent", "SovereignULA/1.0")
                conn.connect()
                val code = conn.responseCode
                if (code in 200..299) {
                    return conn.inputStream
                } else if (code in 300..399) {
                    val loc = conn.getHeaderField("Location")
                    if (!loc.isNullOrBlank()) {
                        currentUrl = loc
                        // follow up to next attempt
                        conn.disconnect()
                        continue
                    } else {
                        throw IOException("Redirect without Location header")
                    }
                } else {
                    throw IOException("HTTP $code")
                }
            } catch (e: UnknownHostException) {
                lastEx = IOException(e)
            } catch (e: IOException) {
                lastEx = e
            }
            if (attempt < attempts) {
                try {
                    Thread.sleep(attemptDelay)
                } catch (_: InterruptedException) {}
                attemptDelay *= 2
            }
        }
        throw lastEx ?: IOException("unknown network error")
    }

    @Throws(IOException::class)
    suspend fun toLines(url: String): List<String> = withContext(Dispatchers.IO) {
        val inputStream = fromUrl(url)
        val reader = BufferedReader(InputStreamReader(inputStream))
        val lines = reader.readLines()
        reader.close()
        return@withContext lines
    }

    @Throws(IOException::class)
    suspend fun toFile(url: String, file: File) = withContext(Dispatchers.IO) {
        file.parentFile?.mkdirs()
        val inputStream = fromUrl(url)
        val outputStream = file.outputStream()
        outputStream.use { out ->
            inputStream.use { inp ->
                inp.copyTo(out)
            }
        }
    }

    @Throws(IOException::class)
    suspend fun toTextFile(url: String, file: File) = withContext(Dispatchers.IO) {
        file.parentFile?.mkdirs()
        val content = URL(url).readText()
        file.writeText(content)
    }
}
