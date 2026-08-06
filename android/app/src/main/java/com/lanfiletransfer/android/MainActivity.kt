package com.lanfiletransfer.android

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ListView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning

class MainActivity : AppCompatActivity() {

    companion object {
        // Must match QR_PAIRING_PREFIX in the PC's gui.py.
        private const val QR_PAIRING_PREFIX = "LANFTSALT1:"
    }

    private lateinit var settingsStore: SettingsStore
    private lateinit var discoveryManager: DiscoveryManager
    private lateinit var deviceListView: ListView
    private lateinit var logView: TextView
    private lateinit var passwordEdit: EditText
    private lateinit var saltEdit: EditText
    private lateinit var deviceNameEdit: EditText

    // key = mDNS service name
    private val devices = linkedMapOf<String, DiscoveredDevice>()
    private lateinit var adapter: ArrayAdapter<String>
    private var selectedDevice: DiscoveredDevice? = null
    private var multicastLock: WifiManager.MulticastLock? = null

    private val logReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val msg = intent?.getStringExtra(TransferServerService.EXTRA_MESSAGE) ?: return
            appendLog(msg)
        }
    }

    private val filePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) sendFile(uri)
    }

    private val notifPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* no-op either way; notifications are a nicety, not required for transfers */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        settingsStore = SettingsStore(this)

        deviceNameEdit = findViewById(R.id.deviceNameEdit)
        passwordEdit = findViewById(R.id.passwordEdit)
        saltEdit = findViewById(R.id.saltEdit)
        deviceListView = findViewById(R.id.deviceListView)
        logView = findViewById(R.id.logView)
        val saveSettingsButton = findViewById<Button>(R.id.saveSettingsButton)
        val sendButton = findViewById<Button>(R.id.sendButton)
        val scanButton = findViewById<Button>(R.id.scanButton)
        val shutdownButton = findViewById<Button>(R.id.shutdownButton)

        deviceNameEdit.setText(settingsStore.getDeviceName())
        passwordEdit.setText(settingsStore.getPassword())
        saltEdit.setText(settingsStore.getSaltHex())

        scanButton.setOnClickListener { launchPairingScanner() }

        adapter = ArrayAdapter(this, android.R.layout.simple_list_item_single_choice, mutableListOf())
        deviceListView.adapter = adapter
        deviceListView.choiceMode = ListView.CHOICE_MODE_SINGLE
        deviceListView.setOnItemClickListener { _, _, position, _ ->
            selectedDevice = devices.values.toList().getOrNull(position)
            appendLog("Selected ${selectedDevice?.hostname}")
        }

        saveSettingsButton.setOnClickListener {
            val saltInput = saltEdit.text.toString()
            if (!CryptoUtil.isValidSaltHex(saltInput)) {
                appendLog("Salt must be a hex string (or empty) — copy \"security_salt\" from the PC's config/config.json.")
            } else {
                settingsStore.setDeviceName(deviceNameEdit.text.toString())
                settingsStore.setPassword(passwordEdit.text.toString())
                settingsStore.setSaltHex(saltInput)
                appendLog("Settings saved. Remember: the password AND salt must match the PC's current config.json.")
            }
        }

        sendButton.setOnClickListener {
            if (selectedDevice == null) {
                appendLog("Select a device from the list first.")
            } else {
                filePicker.launch(arrayOf("*/*"))
            }
        }

        shutdownButton.setOnClickListener { shutDownApp() }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                notifPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        multicastLock = wifiManager.createMulticastLock("lanfiletransfer_activity_lock").apply {
            setReferenceCounted(true)
            acquire()
        }

        discoveryManager = DiscoveryManager(
            this,
            onDeviceFound = { device -> runOnUiThread { addDevice(device) } },
            onDeviceLost = { serviceName -> runOnUiThread { removeDevice(serviceName) } },
        )
        discoveryManager.startDiscovery()

        ContextCompat.registerReceiver(
            this,
            logReceiver,
            IntentFilter(TransferServerService.ACTION_TRANSFER_EVENT),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )

        // Starts the listener + advertises this phone on the LAN so the PC can find it too.
        ContextCompat.startForegroundService(this, Intent(this, TransferServerService::class.java))
    }

    private fun shutDownApp() {
        appendLog("Shutting down...")
        stopService(Intent(this, TransferServerService::class.java))
        discoveryManager.stopDiscovery()
        multicastLock?.release()
        finishAndRemoveTask()
    }

    private fun launchPairingScanner() {
        GmsBarcodeScanning.getClient(this).startScan()
            .addOnSuccessListener { barcode ->
                val raw = barcode.rawValue
                if (raw == null || !raw.startsWith(QR_PAIRING_PREFIX)) {
                    appendLog("Scanned code isn't a LANFileTransfer pairing QR.")
                    return@addOnSuccessListener
                }
                val saltHex = raw.removePrefix(QR_PAIRING_PREFIX).trim()
                if (!CryptoUtil.isValidSaltHex(saltHex) || saltHex.isEmpty()) {
                    appendLog("Scanned salt looks invalid: $saltHex")
                    return@addOnSuccessListener
                }
                saltEdit.setText(saltHex)
                settingsStore.setSaltHex(saltHex)
                appendLog("Salt paired from QR code. Enter the matching password and tap Save.")
            }
            .addOnCanceledListener {
                // user backed out of the scanner; nothing to do
            }
            .addOnFailureListener { e ->
                appendLog("Scan failed: ${e.message}")
            }
    }

    private fun addDevice(device: DiscoveredDevice) {
        devices[device.serviceName] = device
        refreshList()
    }

    private fun removeDevice(serviceName: String) {
        devices.remove(serviceName)
        refreshList()
    }

    private fun refreshList() {
        adapter.clear()
        adapter.addAll(devices.values.map { "${it.hostname} (${it.os}) - ${it.ipAddress}:${it.port}" })
        adapter.notifyDataSetChanged()
    }

    private fun sendFile(uri: Uri) {
        val device = selectedDevice ?: return
        val (name, size) = queryFileInfo(uri)
        appendLog("Sending $name to ${device.hostname}...")
        Thread {
            val result = TransferClient.sendFile(
                contentResolver,
                uri,
                name,
                size,
                device.ipAddress,
                device.port,
                settingsStore.getSecurityKey(),
            )
            runOnUiThread { appendLog(result.message) }
        }.start()
    }

    private fun queryFileInfo(uri: Uri): Pair<String, Long> {
        var name = "file"
        var size = 0L
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIdx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            val sizeIdx = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (cursor.moveToFirst()) {
                if (nameIdx >= 0) name = cursor.getString(nameIdx) ?: name
                if (sizeIdx >= 0) size = cursor.getLong(sizeIdx)
            }
        }
        return name to size
    }

    private fun appendLog(message: String) {
        logView.append("\n$message")
    }

    override fun onDestroy() {
        discoveryManager.stopDiscovery()
        multicastLock?.release()
        try {
            unregisterReceiver(logReceiver)
        } catch (e: Exception) {
        }
        super.onDestroy()
    }
}
