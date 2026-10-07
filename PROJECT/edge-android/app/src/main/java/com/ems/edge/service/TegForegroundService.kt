package com.ems.edge.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.chaquo.python.Python
import com.ems.edge.EmsEdgeApplication
import com.ems.edge.R
import com.ems.edge.data.ConfigRepository
import com.ems.edge.data.TelemetryData
import com.ems.edge.mqtt.MqttManager
import com.ems.edge.ui.MainActivity
import com.google.gson.Gson
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class TegForegroundService : Service() {

    private val tag = "TegForegroundService"
    private var wakeLock: PowerManager.WakeLock? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var pollingJob: Job? = null

    private lateinit var configRepo: ConfigRepository
    private lateinit var mqttManager: MqttManager
    private val gson = Gson()

    companion object {
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"

        private val _latestTelemetry = MutableStateFlow<TelemetryData?>(null)
        val latestTelemetry: StateFlow<TelemetryData?> = _latestTelemetry.asStateFlow()

        private val _isServiceRunning = MutableStateFlow(false)
        val isServiceRunning: StateFlow<Boolean> = _isServiceRunning.asStateFlow()

        private val _mqttStatus = MutableStateFlow("未連線")
        val mqttStatus: StateFlow<String> = _mqttStatus.asStateFlow()
    }

    override fun onCreate() {
        super.onCreate()
        configRepo = ConfigRepository(this)
        mqttManager = MqttManager(this)

        mqttManager.onStatusChanged = { isConnected, message ->
            _mqttStatus.value = if (isConnected) "已連線" else message
        }

        acquireWakeLock()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopForegroundService()
                return START_NOT_STICKY
            }
            ACTION_START, null -> {
                startForegroundService()
            }
        }
        return START_STICKY
    }

    private fun startForegroundService() {
        if (_isServiceRunning.value) return

        _isServiceRunning.value = true
        startForeground(NOTIFICATION_ID, buildNotification("服務啟動中...", "正在連線 TEG 與 MQTT Broker"))

        // 1. 連線 MQTT Broker
        mqttManager.connect(
            host = configRepo.mqttHost,
            port = configRepo.mqttPort,
            siteId = configRepo.siteId,
            username = configRepo.mqttUsername,
            password = configRepo.mqttPassword,
            useTls = configRepo.mqttUseTls
        )

        // 2. 啟動背景協程輪詢迴圈
        pollingJob = serviceScope.launch {
            val py = Python.getInstance()
            val collectorModule = py.getModule("teg_collector")

            while (isActive) {
                try {
                    val rawJson = collectorModule.callAttr(
                        "collect_telemetry",
                        configRepo.tegHost,
                        configRepo.tegPassword,
                        configRepo.tegEmail,
                        configRepo.siteId,
                        configRepo.tegUseSsl
                    ).toString()

                    val telemetry = gson.fromJson(rawJson, TelemetryData::class.java)
                    _latestTelemetry.value = telemetry

                    if (telemetry.isSuccess) {
                        // 發布至 MQTT Broker (Topic: site/{site_id}/telemetry)
                        mqttManager.publishTelemetry(configRepo.siteId, rawJson)

                        // 更新通知欄文字
                        val summary = "太陽: %.1f kW | 電網: %.1f kW | 電池: %.1f kW (%.0f%%)".format(
                            telemetry.solarKw,
                            telemetry.gridKw,
                            telemetry.batteryKw,
                            telemetry.socPct
                        )
                        updateNotification("案場 ${configRepo.siteId} 數據採集中", summary)
                    } else {
                        updateNotification("TEG 連線異常", telemetry.errorMsg.ifEmpty { "無法連線至閘道器" })
                    }

                } catch (e: Exception) {
                    Log.e(tag, "輪詢週期發生異常: ${e.message}", e)
                    updateNotification("採集錯誤", e.message ?: "未知錯誤")
                }

                // 間隔等待
                delay(configRepo.pollIntervalSec * 1000L)
            }
        }
    }

    private fun stopForegroundService() {
        _isServiceRunning.value = false
        pollingJob?.cancel()
        mqttManager.publishStatus(configRepo.siteId, "offline")
        mqttManager.disconnect()
        releaseWakeLock()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun buildNotification(title: String, content: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, EmsEdgeApplication.CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(content)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(title: String, content: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        notificationManager.notify(NOTIFICATION_ID, buildNotification(title, content))
    }

    private fun acquireWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "EmsEdge:TegForegroundServiceWakeLock"
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        wakeLock = null
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        releaseWakeLock()
        mqttManager.disconnect()
        _isServiceRunning.value = false
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
