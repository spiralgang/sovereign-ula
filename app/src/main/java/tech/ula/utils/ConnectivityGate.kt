package tech.ula.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build

class ConnectivityGate(private val context: Context) {
    // Only warn after N consecutive failures AND OS says there's no validated transport
    fun hasValidatedInternet(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }

    fun shouldWarnOffline(consecutiveFailures: Int): Boolean {
        if (consecutiveFailures < 3) return false
        return !hasValidatedInternet()
    }
}
