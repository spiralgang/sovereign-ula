package tech.ula.ui

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import tech.ula.R
import java.io.File

/**
 * Transparent bridge activity that actually MOVES bytes between device storage
 * (via the Storage Access Framework) and the proot/chroot shell environment.
 *
 * Why an Activity: the Edge Panel is a Service and cannot receive
 * onActivityResult, so its file buttons could only *open* a picker — nothing
 * was ever copied in or out. This activity is launched by the Edge Panel with
 * an EXTRA_MODE and performs the real transfer.
 *
 * Where the shell sees the files: BusyboxExecutor.getProotEnv() binds
 *   <getExternalFilesDir(null)>/storage  ->  /storage/internal
 * inside every proot session. So:
 *   IMPORT  copies a device-picked file INTO that dir  -> visible at
 *           /storage/internal/<name> in the shell.
 *   EXPORT  lets the user pick a file already sitting in that dir and copies it
 *           OUT to a device location the user chooses via SAF.
 */
class FileTransferActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_MODE = "mode"
        const val MODE_IMPORT = "import"
        const val MODE_EXPORT = "export"

        private const val REQ_IMPORT_PICK = 4101
        private const val REQ_EXPORT_CREATE = 4102

        /** Subdirectory of getExternalFilesDir(null) that BusyboxExecutor binds
         *  to /storage/internal inside the proot session. */
        const val SHELL_BRIDGE_SUBDIR = "storage"
    }

    /** The device-side directory that maps to /storage/internal in the shell. */
    private val bridgeDir: File
        get() = File(getExternalFilesDir(null), SHELL_BRIDGE_SUBDIR).apply { mkdirs() }

    /** Remembered while the user picks an export destination. */
    private var pendingExportSource: File? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        when (intent.getStringExtra(EXTRA_MODE)) {
            MODE_IMPORT -> startImportPicker()
            MODE_EXPORT -> chooseExportSource()
            else -> {
                toast(getString(R.string.sov_transfer_unknown_mode))
                finish()
            }
        }
    }

    // ---------------------------------------------------------------- IMPORT

    private fun startImportPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivityForResult(intent, REQ_IMPORT_PICK)
        } catch (e: Exception) {
            toast(getString(R.string.sov_transfer_no_picker))
            finish()
        }
    }

    private fun handleImport(uri: Uri) {
        val name = queryDisplayName(uri) ?: "imported_${System.currentTimeMillis()}"
        val dest = uniqueDestination(bridgeDir, name)
        CoroutineScope(Dispatchers.Main).launch {
            val ok = withContext(Dispatchers.IO) {
                try {
                    contentResolver.openInputStream(uri)?.use { input ->
                        dest.outputStream().use { output -> input.copyTo(output) }
                    } != null
                } catch (e: Exception) {
                    false
                }
            }
            if (ok) {
                toast(getString(R.string.sov_transfer_import_success, "/storage/internal/${dest.name}"))
            } else {
                toast(getString(R.string.sov_transfer_import_failure))
            }
            finish()
        }
    }

    // ---------------------------------------------------------------- EXPORT

    private fun chooseExportSource() {
        val files = bridgeDir.listFiles()?.filter { it.isFile }?.sortedBy { it.name.lowercase() }
        if (files.isNullOrEmpty()) {
            toast(getString(R.string.sov_transfer_export_empty))
            finish()
            return
        }
        val names = files.map { it.name }.toTypedArray()
        AlertDialog.Builder(this)
                .setTitle(R.string.sov_transfer_export_pick_title)
                .setItems(names) { _, which ->
                    pendingExportSource = files[which]
                    startExportCreate(files[which].name)
                }
                .setOnCancelListener { finish() }
                .show()
    }

    private fun startExportCreate(suggestedName: String) {
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/octet-stream"
            putExtra(Intent.EXTRA_TITLE, suggestedName)
        }
        try {
            startActivityForResult(intent, REQ_EXPORT_CREATE)
        } catch (e: Exception) {
            toast(getString(R.string.sov_transfer_no_picker))
            finish()
        }
    }

    private fun handleExport(destUri: Uri) {
        val source = pendingExportSource
        if (source == null || !source.exists()) {
            toast(getString(R.string.sov_transfer_export_failure))
            finish()
            return
        }
        CoroutineScope(Dispatchers.Main).launch {
            val ok = withContext(Dispatchers.IO) {
                try {
                    contentResolver.openOutputStream(destUri)?.use { output ->
                        source.inputStream().use { input -> input.copyTo(output) }
                    } != null
                } catch (e: Exception) {
                    false
                }
            }
            if (ok) {
                toast(getString(R.string.sov_transfer_export_success, source.name))
            } else {
                toast(getString(R.string.sov_transfer_export_failure))
            }
            finish()
        }
    }

    // ---------------------------------------------------------------- result

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != Activity.RESULT_OK || data?.data == null) {
            finish()
            return
        }
        when (requestCode) {
            REQ_IMPORT_PICK -> handleImport(data.data!!)
            REQ_EXPORT_CREATE -> handleExport(data.data!!)
            else -> finish()
        }
    }

    // ---------------------------------------------------------------- helpers

    private fun queryDisplayName(uri: Uri): String? {
        return try {
            contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (idx >= 0) c.getString(idx) else null
                } else null
            }
        } catch (e: Exception) {
            null
        }
    }

    /** Avoid clobbering an existing file: append " (n)" before the extension. */
    private fun uniqueDestination(dir: File, name: String): File {
        var candidate = File(dir, name)
        if (!candidate.exists()) return candidate
        val dot = name.lastIndexOf('.')
        val base = if (dot > 0) name.substring(0, dot) else name
        val ext = if (dot > 0) name.substring(dot) else ""
        var i = 1
        while (candidate.exists()) {
            candidate = File(dir, "$base ($i)$ext")
            i++
        }
        return candidate
    }

    private fun toast(msg: String) {
        Toast.makeText(applicationContext, msg, Toast.LENGTH_LONG).show()
    }
}
