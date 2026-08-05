package com.lanfiletransfer.android

import java.io.InputStream
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Matches config.py's derive_key(): PBKDF2-HMAC-SHA256, 200_000 iterations, 256-bit key.
 *
 * config.py generates a random 16-byte salt per PC install and stores it locally in
 * config/config.json (as `security_salt`, hex-encoded) — it is intentionally NOT a
 * fixed/shared constant, to avoid weakening the key derivation. That means this app
 * cannot compute a matching key from the password alone: the same salt hex string
 * from the PC's config.json must be entered into this app's Settings screen too.
 */
object CryptoUtil {

    private const val ITERATIONS = 200_000
    private const val KEY_LENGTH_BITS = 256

    /**
     * Empty password OR empty salt means "no security code configured" -> matches
     * the PC's default empty key (get_security_key() returns b"" until a code has
     * been set via set_new_code()).
     */
    fun deriveSecurityKey(password: String, saltHex: String): ByteArray {
        if (password.isEmpty() || saltHex.isEmpty()) return ByteArray(0)
        val salt = try {
            hexToBytes(saltHex.trim())
        } catch (e: Exception) {
            throw IllegalArgumentException("Salt must be a valid hex string copied from the PC's config.json.")
        }
        val spec = PBEKeySpec(password.toCharArray(), salt, ITERATIONS, KEY_LENGTH_BITS)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        return try {
            factory.generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }

    /** hmac.new(key, nonce.encode("utf-8"), hashlib.sha256).hexdigest() */
    fun hmacSha256Hex(key: ByteArray, message: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        // Java's SecretKeySpec rejects a zero-length key, but Python's hmac.new(b"", ...)
        // accepts one fine. Per the HMAC spec, keys shorter than the hash's block size
        // (64 bytes for SHA-256) are zero-padded internally before use, so an empty key
        // is mathematically identical to a 64-byte all-zero key. We pass that explicitly
        // to reproduce Python's output exactly when no password has been set.
        val effectiveKey = if (key.isEmpty()) ByteArray(64) else key
        mac.init(SecretKeySpec(effectiveKey, "HmacSHA256"))
        return bytesToHex(mac.doFinal(message.toByteArray(Charsets.UTF_8)))
    }

    /** secrets.token_hex(16) */
    fun randomNonceHex(): String {
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        return bytesToHex(bytes)
    }

    /** hashlib.sha256() over the full stream, 1 MiB chunks. */
    fun sha256Hex(stream: InputStream): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(1 shl 20)
        while (true) {
            val read = stream.read(buffer)
            if (read == -1) break
            digest.update(buffer, 0, read)
        }
        return bytesToHex(digest.digest())
    }

    /** True for an empty string (no salt configured yet) or a well-formed hex string. */
    fun isValidSaltHex(hex: String): Boolean {
        val trimmed = hex.trim()
        if (trimmed.isEmpty()) return true
        if (trimmed.length % 2 != 0) return false
        return trimmed.all { it.isDigit() || it.lowercaseChar() in 'a'..'f' }
    }

    fun bytesToHex(bytes: ByteArray): String {
        val sb = StringBuilder(bytes.size * 2)
        for (b in bytes) sb.append(String.format("%02x", b))
        return sb.toString()
    }

    private fun hexToBytes(hex: String): ByteArray {
        require(hex.length % 2 == 0) { "Hex string must have an even length." }
        return ByteArray(hex.length / 2) { i ->
            ((Character.digit(hex[i * 2], 16) shl 4) + Character.digit(hex[i * 2 + 1], 16)).toByte()
        }
    }
}
