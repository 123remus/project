package com.ems.edge.data

import android.content.Context
import android.content.SharedPreferences

class ConfigRepository(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("ems_edge_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_SITE_ID = "site_id"
        private const val KEY_TEG_HOST = "teg_host"
        private const val KEY_TEG_PASSWORD = "teg_password"
        private const val KEY_TEG_EMAIL = "teg_email"
        private const val KEY_TEG_USE_SSL = "teg_use_ssl"

        private const val KEY_MQTT_HOST = "mqtt_host"
        private const val KEY_MQTT_PORT = "mqtt_port"
        private const val KEY_MQTT_USERNAME = "mqtt_username"
        private const val KEY_MQTT_PASSWORD = "mqtt_password"
        private const val KEY_MQTT_USE_TLS = "mqtt_use_tls"

        private const val KEY_POLL_INTERVAL = "poll_interval_sec"
        private const val KEY_AUTO_START_BOOT = "auto_start_boot"
        private const val KEY_CLOUD_API_URL = "cloud_api_url"
    }

    var siteId: String
        get() = prefs.getString(KEY_SITE_ID, "site_01") ?: "site_01"
        set(value) = prefs.edit().putString(KEY_SITE_ID, value).apply()

    var tegHost: String
        get() = prefs.getString(KEY_TEG_HOST, "192.168.50.177:8675") ?: "192.168.50.177:8675"
        set(value) = prefs.edit().putString(KEY_TEG_HOST, value).apply()

    var tegPassword: String
        get() = prefs.getString(KEY_TEG_PASSWORD, "mock_password") ?: "mock_password"
        set(value) = prefs.edit().putString(KEY_TEG_PASSWORD, value).apply()

    var tegEmail: String
        get() = prefs.getString(KEY_TEG_EMAIL, "customer@example.com") ?: "customer@example.com"
        set(value) = prefs.edit().putString(KEY_TEG_EMAIL, value).apply()

    var tegUseSsl: Boolean
        get() = prefs.getBoolean(KEY_TEG_USE_SSL, false)
        set(value) = prefs.edit().putBoolean(KEY_TEG_USE_SSL, value).apply()

    var mqttHost: String
        get() = prefs.getString(KEY_MQTT_HOST, "broker.emqx.io") ?: "broker.emqx.io"
        set(value) = prefs.edit().putString(KEY_MQTT_HOST, value).apply()

    var mqttPort: Int
        get() = prefs.getInt(KEY_MQTT_PORT, 1883)
        set(value) = prefs.edit().putInt(KEY_MQTT_PORT, value).apply()

    var mqttUsername: String
        get() = prefs.getString(KEY_MQTT_USERNAME, "") ?: ""
        set(value) = prefs.edit().putString(KEY_MQTT_USERNAME, value).apply()

    var mqttPassword: String
        get() = prefs.getString(KEY_MQTT_PASSWORD, "") ?: ""
        set(value) = prefs.edit().putString(KEY_MQTT_PASSWORD, value).apply()

    var mqttUseTls: Boolean
        get() = prefs.getBoolean(KEY_MQTT_USE_TLS, false)
        set(value) = prefs.edit().putBoolean(KEY_MQTT_USE_TLS, value).apply()

    var pollIntervalSec: Int
        get() = prefs.getInt(KEY_POLL_INTERVAL, 3)
        set(value) = prefs.edit().putInt(KEY_POLL_INTERVAL, value).apply()

    var autoStartOnBoot: Boolean
        get() = prefs.getBoolean(KEY_AUTO_START_BOOT, true)
        set(value) = prefs.edit().putBoolean(KEY_AUTO_START_BOOT, value).apply()

    var cloudApiUrl: String
        get() = prefs.getString(KEY_CLOUD_API_URL, "http://192.168.50.177:8000") ?: "http://192.168.50.177:8000"
        set(value) = prefs.edit().putString(KEY_CLOUD_API_URL, value).apply()
}
