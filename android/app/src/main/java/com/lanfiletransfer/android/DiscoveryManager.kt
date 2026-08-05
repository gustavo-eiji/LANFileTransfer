package com.lanfiletransfer.android

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log

data class DiscoveredDevice(
    val deviceId: String,
    val hostname: String,
    val ipAddress: String,
    val port: Int,
    val os: String,
    val version: String,
    val serviceName: String,
)

/**
 * Uses Android's NsdManager (mDNS/DNS-SD) to interoperate with the PC's Zeroconf
 * based discovery.py. Service type and TXT record keys (device_id, os, version,
 * hostname) match discovery.py exactly.
 */
class DiscoveryManager(
    private val context: Context,
    private val onDeviceFound: (DiscoveredDevice) -> Unit,
    private val onDeviceLost: (String) -> Unit,
) {
    companion object {
        // Matches settings.py: DISCOVERY_SERVICE = "_lanfiletransfer._tcp.local."
        // Android's NsdManager wants the type without the trailing ".local." domain.
        const val SERVICE_TYPE = "_lanfiletransfer._tcp."
        private const val TAG = "DiscoveryManager"
    }

    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var registrationListener: NsdManager.RegistrationListener? = null

    fun startDiscovery() {
        val listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {
                Log.i(TAG, "Discovery started")
            }

            override fun onServiceFound(service: NsdServiceInfo) {
                if (!service.serviceType.contains("lanfiletransfer")) return
                resolve(service)
            }

            override fun onServiceLost(service: NsdServiceInfo) {
                onDeviceLost(service.serviceName)
            }

            override fun onDiscoveryStopped(serviceType: String) {}

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Start discovery failed: $errorCode")
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
        }
        discoveryListener = listener
        try {
            nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener)
        } catch (e: Exception) {
            Log.e(TAG, "discoverServices failed: ${e.message}")
        }
    }

    @Suppress("DEPRECATION")
    private fun resolve(service: NsdServiceInfo) {
        nsdManager.resolveService(service, object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Resolve failed for ${serviceInfo.serviceName}: $errorCode")
            }

            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                val attrs = serviceInfo.attributes ?: emptyMap()
                fun attr(key: String): String? = attrs[key]?.toString(Charsets.UTF_8)

                val deviceId = attr("device_id") ?: return
                val hostname = attr("hostname") ?: return
                val os = attr("os") ?: "unknown"
                val version = attr("version") ?: "unknown"
                val host = serviceInfo.host?.hostAddress ?: return
                val port = serviceInfo.port

                onDeviceFound(
                    DiscoveredDevice(
                        deviceId = deviceId,
                        hostname = hostname,
                        ipAddress = host,
                        port = port,
                        os = os,
                        version = version,
                        serviceName = serviceInfo.serviceName,
                    )
                )
            }
        })
    }

    fun stopDiscovery() {
        discoveryListener?.let {
            try {
                nsdManager.stopServiceDiscovery(it)
            } catch (e: Exception) {
                Log.w(TAG, "stopServiceDiscovery: ${e.message}")
            }
        }
        discoveryListener = null
    }

    /** Advertise this phone so it also shows up in the PC's device list. */
    fun registerService(port: Int, deviceId: String, hostname: String) {
        val serviceInfo = NsdServiceInfo().apply {
            serviceName = hostname
            serviceType = SERVICE_TYPE
            setPort(port)
            setAttribute("device_id", deviceId)
            setAttribute("os", "Android")
            setAttribute("version", BuildConfig.VERSION_NAME)
            setAttribute("hostname", hostname)
        }
        val listener = object : NsdManager.RegistrationListener {
            override fun onServiceRegistered(info: NsdServiceInfo) {
                Log.i(TAG, "Registered as ${info.serviceName}")
            }

            override fun onRegistrationFailed(info: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Registration failed: $errorCode")
            }

            override fun onServiceUnregistered(info: NsdServiceInfo) {}
            override fun onUnregistrationFailed(info: NsdServiceInfo, errorCode: Int) {}
        }
        registrationListener = listener
        try {
            nsdManager.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, listener)
        } catch (e: Exception) {
            Log.e(TAG, "registerService failed: ${e.message}")
        }
    }

    fun unregisterService() {
        registrationListener?.let {
            try {
                nsdManager.unregisterService(it)
            } catch (e: Exception) {
                Log.w(TAG, "unregisterService: ${e.message}")
            }
        }
        registrationListener = null
    }
}
