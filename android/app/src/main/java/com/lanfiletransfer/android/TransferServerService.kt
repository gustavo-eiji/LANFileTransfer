package com.lanfiletransfer.android

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.provider.MediaStore
import android.util.Log
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import java.io.IOException
import java.net.ServerSocket
import java.net.Socket
import java.security.MessageDigest

/** Mirrors TransferServer in transfer.py, adapted to Android's storage model. */
class TransferServerService : Service() {

    companion object {
        const val CHANNEL_ID = "lan_file_transfer_service"
        const val NOTIF_ID = 1
        const val PORT = 50007 // matches settings.py TRANSFER_PORT
        private const val TAG = "TransferServer"
        const val ACTION_TRANSFER_EVENT = "com.lanfiletransfer.android.TRANSFER_EVENT"
        const val EXTRA_MESSAGE = "message"
    }

    private var serverSocket: ServerSocket? = null
    private var discoveryManager: DiscoveryManager? = null
    private var multicastLock: WifiManager.MulticastLock? = null

    @Volatile
    private var running = false
    private lateinit var settingsStore: SettingsStore

    override fun onCreate() {
        super.onCreate()
        settingsStore = SettingsStore(this)
        createNotificationChannel()

        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        multicastLock = wifiManager.createMulticastLock("lanfiletransfer_server_lock").apply {
            setReferenceCounted(true)
            acquire()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("LANFileTransfer")
            .setContentText("Listening for incoming transfers on port $PORT")
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIF_ID, notification)
        }

        if (!running) {
            running = true
            Thread { runServer() }.start()
            discoveryManager = DiscoveryManager(this, {}, {}).also {
                it.registerService(PORT, settingsStore.getDeviceId(), settingsStore.getDeviceName())
            }
        }
        return START_STICKY
    }

    private fun runServer() {
        try {
            val socket = ServerSocket(PORT)
            serverSocket = socket
            Log.i(TAG, "Listening on port $PORT")
            while (running) {
                val client = try {
                    socket.accept()
                } catch (e: Exception) {
                    break
                }
                Thread { handleClient(client) }.start()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Server error: ${e.message}")
            notifyEvent("Could not start listener: ${e.message}")
        }
    }

    private fun handleClient(socket: Socket) {
        socket.use { conn ->
            conn.soTimeout = 30_000 // matches settings.py SOCKET_TIMEOUT
            val message = try {
                PacketIO.receivePacket(conn.getInputStream())
            } catch (e: Exception) {
                null
            } ?: return

            if (message.type != "FILE_OFFER") {
                // Other message types (PING/TEXT/etc.) aren't needed for this app's scope.
                return
            }

            val payload = message.payload
            val filename = payload.optString("filename")
            val filesize = payload.optLong("filesize", -1)
            val expectedHash = payload.optString("sha256")
            val nonce = if (payload.has("nonce")) payload.optString("nonce") else null
            val hmacValue = if (payload.has("hmac")) payload.optString("hmac") else null

            if (filename.isNullOrEmpty() || filesize < 0 || nonce == null || hmacValue == null) {
                sendReject(conn, "Client uses incompatible protocol")
                return
            }

            val securityKey = settingsStore.getSecurityKey()
            val expectedHmac = CryptoUtil.hmacSha256Hex(securityKey, nonce)
            if (!constantTimeEquals(hmacValue, expectedHmac)) {
                sendReject(conn, "Authentication failed")
                return
            }

            PacketIO.sendPacket(conn.getOutputStream(), Message("FILE_ACCEPT", JSONObject()))
            receiveFile(conn, filename, filesize, expectedHash)
        }
    }

    private fun constantTimeEquals(a: String, b: String): Boolean =
        MessageDigest.isEqual(a.toByteArray(Charsets.UTF_8), b.toByteArray(Charsets.UTF_8))

    private fun sendReject(conn: Socket, reason: String) {
        try {
            PacketIO.sendPacket(conn.getOutputStream(), Message("FILE_REJECT", JSONObject().put("reason", reason)))
        } catch (e: Exception) {
            // connection likely already gone; nothing more to do
        }
        notifyEvent("Rejected incoming transfer: $reason")
    }

    private fun receiveFile(conn: Socket, filename: String, filesize: Long, expectedHash: String) {
        val resolver = contentResolver
        val safeName = filename
            .substringAfterLast('/')
            .substringAfterLast('\\')
            .ifBlank { "received_file" }

        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, safeName)
            put(MediaStore.Downloads.RELATIVE_PATH, "Download/LANFileTransfer")
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        val itemUri: Uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: run {
            notifyEvent("Failed to save $safeName")
            return
        }

        val digest = MessageDigest.getInstance("SHA-256")
        var received = 0L
        try {
            resolver.openOutputStream(itemUri)?.use { out ->
                val input = conn.getInputStream()
                val buffer = ByteArray(64 * 1024)
                while (received < filesize) {
                    val toRead = minOf(buffer.size.toLong(), filesize - received).toInt()
                    val read = input.read(buffer, 0, toRead)
                    if (read == -1) throw IOException("Connection lost during transfer.")
                    out.write(buffer, 0, read)
                    digest.update(buffer, 0, read)
                    received += read
                }
            } ?: throw IOException("Unable to open output stream for $safeName.")

            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(itemUri, values, null, null)

            val receivedHash = CryptoUtil.bytesToHex(digest.digest())
            if (receivedHash.equals(expectedHash, ignoreCase = true)) {
                notifyEvent("Received $safeName")
            } else {
                notifyEvent("Integrity check failed for $safeName - deleted")
                resolver.delete(itemUri, null, null)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Transfer failed: ${e.message}")
            try {
                resolver.delete(itemUri, null, null)
            } catch (ignored: Exception) {
            }
            notifyEvent("Transfer failed: ${e.message}")
        }
    }

    private fun notifyEvent(message: String) {
        sendBroadcast(Intent(ACTION_TRANSFER_EVENT).setPackage(packageName).putExtra(EXTRA_MESSAGE, message))
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("LANFileTransfer")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setAutoCancel(true)
            .build()
        val manager = getSystemService(NotificationManager::class.java)
        manager?.notify((NOTIF_ID + 1000 + (System.currentTimeMillis() % 1000)).toInt(), notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "LAN File Transfer", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        running = false
        try {
            serverSocket?.close()
        } catch (e: Exception) {
        }
        discoveryManager?.unregisterService()
        multicastLock?.release()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
