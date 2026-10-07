package com.ems.edge.data

import com.google.gson.annotations.SerializedName

/**
 * 遙測數據模型
 * 符合工業 EMS 與雲端 Ingestion Worker 規範的標準 Payload
 */
data class TelemetryData(
    @SerializedName("site_id")
    val siteId: String = "site_01",

    @SerializedName("timestamp")
    val timestamp: Long = System.currentTimeMillis() / 1000,

    @SerializedName("solar_kw")
    val solarKw: Double = 0.0,

    @SerializedName("grid_kw")
    val gridKw: Double = 0.0,

    @SerializedName("battery_kw")
    val batteryKw: Double = 0.0,

    @SerializedName("home_kw")
    val homeKw: Double = 0.0,

    @SerializedName("soc_pct")
    val socPct: Double = 0.0,

    @SerializedName("grid_status")
    val gridStatus: String = "Connected",

    @SerializedName("is_success")
    val isSuccess: Boolean = true,

    @SerializedName("error_msg")
    val errorMsg: String = ""
)
