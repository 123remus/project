package com.ems.edge.mqtt

import android.content.Context
import android.util.Log
import com.google.gson.JsonObject
import org.eclipse.paho.client.mqttv3.*
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import java.security.SecureRandom
import java.security.cert.X509Certificate
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class MqttManager(private val context: Context) {

    private val tag = "MqttManager"
    private var client: MqttAsyncClient? = null
    var isConnected: Boolean = false
        private set

    var onStatusChanged: ((Boolean, String) -> Unit)? = null

    /**
     * 建立連線並設定 TLS 與 LWT (Last Will and Testament)
     */
    fun connect(
        host: String,
        port: Int,
        siteId: String,
        username: String = "",
        password: String = "",
        useTls: Boolean = false
    ) {
        val protocol = if (useTls) "ssl" else "tcp"
        val serverUri = "$protocol://$host:$port"
        val clientId = "ems-android-${siteId}-${System.currentTimeMillis() % 10000}"

        try {
            client?.disconnect()
            client?.close()
        } catch (_: Exception) {}

        try {
            client = MqttAsyncClient(serverUri, clientId, MemoryPersistence())

            val options = MqttConnectOptions().apply {
                isCleanSession = true
                isAutomaticReconnect = true
                keepAliveInterval = 30
                connectionTimeout = 10

                if (username.isNotEmpty()) {
                    userName = username
                    this.password = password.toCharArray()
                }

                if (useTls) {
                    socketFactory = createTrustAllSocketFactory()
                }

                // 設定遺囑訊息 (LWT): 若邊緣端異常斷線，Broker 自動通知雲端
                val lwtJson = JsonObject().apply {
                    addProperty("site_id", siteId)
                    addProperty("status", "offline")
                    addProperty("timestamp", System.currentTimeMillis() / 1000)
                }
                setWill("site/$siteId/status", lwtJson.toString().toByteArray(), 1, true)
            }

            client?.setCallback(object : MqttCallbackExtended {
                override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                    isConnected = true
                    Log.i(tag, "MQTT 連線成功 (重連: $reconnect): $serverURI")
                    onStatusChanged?.invoke(true, "已連線")
                    // 發布上線訊息
                    publishStatus(siteId, "online")
                }

                override fun connectionLost(cause: Throwable?) {
                    isConnected = false
                    Log.w(tag, "MQTT 連線中斷: ${cause?.message}")
                    onStatusChanged?.invoke(false, "連線中斷: ${cause?.message ?: "未知原因"}")
                }

                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    Log.d(tag, "收到訊息: $topic -> ${message?.toString()}")
                }

                override fun deliveryComplete(token: IMqttDeliveryToken?) {}
            })

            Log.i(tag, "正在連線至 MQTT Broker: $serverUri")
            client?.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    isConnected = true
                    onStatusChanged?.invoke(true, "連線成功")
                }

                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    isConnected = false
                    Log.e(tag, "MQTT 連線失敗: ${exception?.message}")
                    onStatusChanged?.invoke(false, "連線失敗: ${exception?.message}")
                }
            })

        } catch (e: Exception) {
            isConnected = false
            Log.e(tag, "初始化 MQTT 異常: ${e.message}", e)
            onStatusChanged?.invoke(false, "初始化異常: ${e.message}")
        }
    }

    /**
     * 發布遙測數據至 site/{siteId}/telemetry (QoS 1)
     */
    fun publishTelemetry(siteId: String, jsonPayload: String, onComplete: ((Boolean) -> Unit)? = null) {
        if (client == null || !isConnected) {
            onComplete?.invoke(false)
            return
        }

        val topic = "site/$siteId/telemetry"
        try {
            val message = MqttMessage(jsonPayload.toByteArray()).apply {
                qos = 1
                isRetained = false
            }
            client?.publish(topic, message, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    onComplete?.invoke(true)
                }

                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.e(tag, "發布遙測失敗: ${exception?.message}")
                    onComplete?.invoke(false)
                }
            })
        } catch (e: Exception) {
            Log.e(tag, "發布遙測發生異常: ${e.message}")
            onComplete?.invoke(false)
        }
    }

    /**
     * 發布案場狀態 (online / offline) 至 site/{siteId}/status
     */
    fun publishStatus(siteId: String, status: String) {
        val topic = "site/$siteId/status"
        val payload = JsonObject().apply {
            addProperty("site_id", siteId)
            addProperty("status", status)
            addProperty("timestamp", System.currentTimeMillis() / 1000)
        }.toString()

        try {
            val message = MqttMessage(payload.toByteArray()).apply {
                qos = 1
                isRetained = true
            }
            client?.publish(topic, message)
        } catch (_: Exception) {}
    }

    fun disconnect() {
        try {
            if (isConnected) {
                client?.disconnect()
            }
            client?.close()
        } catch (_: Exception) {}
        isConnected = false
    }

    /**
     * 建立相容自簽憑證的 SSL SocketFactory (針對 MQTTS TLS 測試環境)
     */
    private fun createTrustAllSocketFactory(): javax.net.ssl.SSLSocketFactory {
        val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>?, authType: String?) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        })

        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, trustAllCerts, SecureRandom())
        return sslContext.socketFactory
    }
}
