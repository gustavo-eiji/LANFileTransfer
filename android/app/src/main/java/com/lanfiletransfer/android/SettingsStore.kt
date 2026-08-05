package com.lanfiletransfer.android

import android.content.Context
import android.os.Build
import java.util.UUID

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("lanfiletransfer_prefs", Context.MODE_PRIVATE)

    fun getDeviceId(): String {
        var id = prefs.getString("device_id", null)
        if (id == null) {
            id = UUID.randomUUID().toString()
            prefs.edit().putString("device_id", id).apply()
        }
        return id
    }

    fun getDeviceName(): String =
        prefs.getString("device_name", null) ?: (Build.MODEL ?: "Android Device")

    fun setDeviceName(name: String) {
        prefs.edit().putString("device_name", name.ifBlank { getDeviceName() }).apply()
    }

    fun getPassword(): String = prefs.getString("password", "") ?: ""

    fun setPassword(password: String) {
        prefs.edit().putString("password", password).apply()
    }

    /**
     * The salt hex string copied from the PC's config/config.json ("security_salt").
     * Required alongside the password for a matching key — see CryptoUtil.
     */
    fun getSaltHex(): String = prefs.getString("salt_hex", "") ?: ""

    fun setSaltHex(saltHex: String) {
        prefs.edit().putString("salt_hex", saltHex.trim()).apply()
    }

    /** Empty password or salt -> empty key, matching the PC's "no security code set" state. */
    fun getSecurityKey(): ByteArray = CryptoUtil.deriveSecurityKey(getPassword(), getSaltHex())
}
