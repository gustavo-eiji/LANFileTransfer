package com.lanfiletransfer.android

import org.json.JSONObject
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.InputStream
import java.io.OutputStream

/**
 * Mirrors LANFileTransfer's protocol.py.
 *
 * IMPORTANT: PROTOCOL.md (the repo's own docs) describes the JSON key as
 * "message_type", but the actual Python implementation (protocol.py) sends
 * the key as "type". This file matches the real code, not the docs.
 */
object ProtocolConstants {
    const val MAGIC = "LANFILETRANSFER"
    const val VERSION = 1
}

data class Message(val type: String, val payload: JSONObject)

object MessageCodec {

    fun encode(message: Message): ByteArray {
        val obj = JSONObject()
        obj.put("magic", ProtocolConstants.MAGIC)
        obj.put("version", ProtocolConstants.VERSION)
        obj.put("type", message.type)
        obj.put("payload", message.payload)
        return obj.toString().toByteArray(Charsets.UTF_8)
    }

    fun decode(data: ByteArray): Message {
        val obj = JSONObject(String(data, Charsets.UTF_8))
        if (obj.optString("magic") != ProtocolConstants.MAGIC) {
            throw IllegalArgumentException("Invalid protocol identifier.")
        }
        if (obj.optInt("version") != ProtocolConstants.VERSION) {
            throw IllegalArgumentException("Invalid protocol version: ${obj.opt("version")}")
        }
        val type = obj.getString("type")
        val payload = obj.optJSONObject("payload") ?: JSONObject()
        return Message(type, payload)
    }
}

/**
 * Every packet is a 4-byte big-endian ("network byte order") length prefix
 * followed by that many bytes of UTF-8 JSON. This matches struct.pack("!I", ...)
 * on the Python side. File bytes themselves are NOT wrapped in this framing;
 * they are streamed raw right after a FILE_ACCEPT.
 */
object PacketIO {

    fun sendPacket(out: OutputStream, message: Message) {
        val data = MessageCodec.encode(message)
        val dos = DataOutputStream(out)
        dos.writeInt(data.size) // big-endian, matches "!I"
        dos.write(data)
        dos.flush()
    }

    /** Returns null on clean connection close (mirrors recv_exact returning None). */
    fun receivePacket(input: InputStream): Message? {
        val dis = DataInputStream(input)
        val length = try {
            dis.readInt()
        } catch (e: Exception) {
            return null
        }
        if (length < 0 || length > 64 * 1024 * 1024) {
            // Sanity cap for a JSON control message (not the file stream itself).
            throw IllegalArgumentException("Unreasonable message length: $length")
        }
        val buffer = ByteArray(length)
        dis.readFully(buffer)
        return MessageCodec.decode(buffer)
    }
}
