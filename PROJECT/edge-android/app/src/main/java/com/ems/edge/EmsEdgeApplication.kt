package com.ems.edge

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class EmsEdgeApplication : Application() {

    companion object {
        const val CHANNEL_ID = "ems_telemetry_channel"
        const val CHANNEL_NAME = "EMS 邊緣數據採集通道"
    }

    override fun onCreate() {
        super.onCreate()

        // 1. 初始化 Chaquopy Python Runtime
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        // 2. 建立前台服務所需的 Notification Channel
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Tesla Powerwall 邊緣端遙測數據採集與 MQTTS 串流服務通知"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }
}
