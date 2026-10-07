package com.ems.edge.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.ems.edge.data.ConfigRepository
import com.ems.edge.service.TegForegroundService

class BootReceiver : BroadcastReceiver() {

    private val tag = "BootReceiver"

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        if (Intent.ACTION_BOOT_COMPLETED == action || "android.intent.action.QUICKBOOT_POWERON" == action) {
            val configRepo = ConfigRepository(context)
            if (configRepo.autoStartOnBoot) {
                Log.i(tag, "裝置開機完成，正在自動啟動 EMS 邊緣常駐採集服務...")
                val serviceIntent = Intent(context, TegForegroundService::class.java).apply {
                    this.action = TegForegroundService.ACTION_START
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
            } else {
                Log.i(tag, "開機自啟動設定已停用，不啟動服務。")
            }
        }
    }
}
