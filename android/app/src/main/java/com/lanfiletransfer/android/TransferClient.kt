package com.lanfiletransfer.android

import android.content.ContentResolver
import android.net.Uri
import org.json.JSONObject
import java.io.BufferedInputStream
import java.net.InetSocketAddress
import java.net.Socket

/** Mirrors TransferClient in transfer.py. */
object TransferClient {

    data class SendResult(val success: Boolean, val message: String)

    fun sendFile(
        contentResolver: ContentResolver,
        uri: Uri,
        fileName: String,
        fileSize: Long,
        host: String,
        port: Int,
        securityKey: ByteArray,
        socketTimeoutMs: Int = 30_000,
        onProgress: ((Int) -> Unit)? = null,
    ): SendResult {
        val sha256 = try {
            contentResolver.openInputStream(uri)?.use { CryptoUtil.sha256Hex(it) }
                ?: return SendResult(false, "Unable to read file.")
        } catch (e: Exception) {
            return SendResult(false, "Unable to hash file: ${e.message}")
        }

        val nonce = CryptoUtil.randomNonceHex()
        val proof = CryptoUtil.hmacSha256Hex(securityKey, nonce)

        return try {
            Socket().use { socket ->
                socket.connect(InetSocketAddress(host, port), socketTimeoutMs)
                socket.soTimeout = socketTimeoutMs

                val payload = JSONObject().apply {
                    put("filename", fileName)
                    put("filesize", fileSize)
                    put("sha256", sha256)
                    put("nonce", nonce)
                    put("hmac", proof)
                }
                PacketIO.sendPacket(socket.getOutputStream(), Message("FILE_OFFER", payload))

                val reply = PacketIO.receivePacket(socket.getInputStream())
                    ?: return SendResult(false, "Connection closed by remote device.")

                when (reply.type) {
                    "FILE_REJECT" -> {
                        val reason = reply.payload.optString("reason", "Transfer rejected.")
                        return SendResult(false, reason)
                    }
                    "FILE_ACCEPT" -> {
                        streamFile(contentResolver, uri, fileSize, socket, onProgress)
                        SendResult(true, "Transfer completed: $fileName")
                    }
                    else -> SendResult(false, "Unexpected response: ${reply.type}")
                }
            }
        } catch (e: Exception) {
            SendResult(false, "Transfer failed: ${e.message}")
        }
    }

    private fun streamFile(
        contentResolver: ContentResolver,
        uri: Uri,
        fileSize: Long,
        socket: Socket,
        onProgress: ((Int) -> Unit)?,
    ) {
        val out = socket.getOutputStream()
        contentResolver.openInputStream(uri)?.use { input ->
            val buffered = BufferedInputStream(input)
            val buffer = ByteArray(64 * 1024) // matches TRANSFER_BUFFER_SIZE in settings.py
            var sent = 0L
            while (true) {
                val read = buffered.read(buffer)
                if (read == -1) break
                out.write(buffer, 0, read)
                sent += read
                if (fileSize > 0) {
                    onProgress?.invoke(((sent * 100) / fileSize).toInt())
                }
            }
            out.flush()
        } ?: throw java.io.IOException("Unable to reopen file for streaming.")
    }
}
