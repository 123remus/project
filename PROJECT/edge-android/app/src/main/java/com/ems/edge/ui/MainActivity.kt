package com.ems.edge.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.ems.edge.data.ConfigRepository
import com.ems.edge.service.TegForegroundService
import com.ems.edge.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {

    private lateinit var configRepo: ConfigRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configRepo = ConfigRepository(this)

        setContent {
            EmsEdgeTheme {
                val context = LocalContext.current
                val permissionLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.RequestPermission()
                ) { isGranted ->
                    if (isGranted) {
                        startCollectorService()
                    } else {
                        Toast.makeText(context, "請允許通知權限以維持背景持續採集服務", Toast.LENGTH_LONG).show()
                        startCollectorService()
                    }
                }

                MainScreen(
                    configRepo = configRepo,
                    onStartService = {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                        ) {
                            permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else {
                            startCollectorService()
                        }
                    },
                    onStopService = { stopCollectorService() },
                    onRequestBatteryExemption = { requestBatteryExemption() }
                )
            }
        }
    }

    private fun startCollectorService() {
        val intent = Intent(this, TegForegroundService::class.java).apply {
            action = TegForegroundService.ACTION_START
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopCollectorService() {
        val intent = Intent(this, TegForegroundService::class.java).apply {
            action = TegForegroundService.ACTION_STOP
        }
        startService(intent)
    }

    @SuppressLint("BatteryLife")
    private fun requestBatteryExemption() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            if (!pm.isIgnoringBatteryOptimizations(packageName)) {
                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
            } else {
                Toast.makeText(this, "系統已加入電池最佳化白名單 (24H 不休眠)", Toast.LENGTH_SHORT).show()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    configRepo: ConfigRepository,
    onStartService: () -> Unit,
    onStopService: () -> Unit,
    onRequestBatteryExemption: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val isRunning by TegForegroundService.isServiceRunning.collectAsState()
    val telemetry by TegForegroundService.latestTelemetry.collectAsState()
    val mqttStatus by TegForegroundService.mqttStatus.collectAsState()
    var showSettingsDialog by remember { mutableStateOf(false) }

    // 雲端遠端控制狀態
    var reserveSlider by remember { mutableStateOf(20f) }
    var controlActionStatus by remember { mutableStateOf<String?>(null) }
    var isSendingControl by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Tesla EMS 智慧儲能系統", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text("案場: ${configRepo.siteId} | TEG: ${configRepo.tegHost}", fontSize = 12.sp, color = TextSecondary)
                    }
                },
                actions = {
                    IconButton(onClick = { showSettingsDialog = true }) {
                        Icon(Icons.Default.Settings, contentDescription = "設定", tint = TextPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkSurface,
                    titleContentColor = TextPrimary
                )
            )
        },
        containerColor = DarkBackground
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. 運行狀態橫幅
            Card(
                colors = CardDefaults.cardColors(containerColor = CardBackground),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(if (isRunning) StatusOnline else StatusOffline, RoundedCornerShape(5.dp))
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isRunning) "前台採集服務運行中" else "採集服務已停止",
                                fontWeight = FontWeight.SemiBold,
                                color = if (isRunning) StatusOnline else StatusOffline
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "MQTT 連線: $mqttStatus",
                            fontSize = 13.sp,
                            color = TextSecondary
                        )
                    }

                    Button(
                        onClick = { if (isRunning) onStopService() else onStartService() },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isRunning) Color(0xFFD32F2F) else BatteryGreen
                        )
                    ) {
                        Text(if (isRunning) "停止服務" else "啟動服務", color = Color.White)
                    }
                }
            }

            // 2. 即時功率儀表卡片 (4大指標)
            Text("即時電表功率 (kW)", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = TextPrimary)

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "太陽能",
                    value = "%.2f".format(telemetry?.solarKw ?: 0.0),
                    unit = "kW",
                    icon = Icons.Default.WbSunny,
                    accentColor = SolarYellow,
                    subtitle = "即時發電"
                )
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "電網",
                    value = "%.2f".format(telemetry?.gridKw ?: 0.0),
                    unit = "kW",
                    icon = Icons.Default.Power,
                    accentColor = GridBlue,
                    subtitle = if ((telemetry?.gridKw ?: 0.0) < 0) "回售電網" else "市電輸入"
                )
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "電池儲能",
                    value = "%.2f".format(telemetry?.batteryKw ?: 0.0),
                    unit = "kW",
                    icon = Icons.Default.BatteryChargingFull,
                    accentColor = BatteryGreen,
                    subtitle = if ((telemetry?.batteryKw ?: 0.0) >= 0) "充電中" else "放電中"
                )
                MetricCard(
                    modifier = Modifier.weight(1f),
                    title = "家庭負載",
                    value = "%.2f".format(telemetry?.homeKw ?: 0.0),
                    unit = "kW",
                    icon = Icons.Default.Home,
                    accentColor = HomePurple,
                    subtitle = "總用電量"
                )
            }

            // 3. 電池電量百分比 (SoC)
            Card(
                colors = CardDefaults.cardColors(containerColor = CardBackground),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("電池可用電量 (SoC)", fontWeight = FontWeight.SemiBold, color = TextPrimary)
                        Text(
                            "%.1f%%".format(telemetry?.socPct ?: 0.0),
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            color = BatteryGreen
                        )
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    LinearProgressIndicator(
                        progress = ((telemetry?.socPct ?: 0.0) / 100.0).toFloat().coerceIn(0f, 1f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp),
                        color = BatteryGreen,
                        trackColor = Color(0xFF333333)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("電網連接: ${telemetry?.gridStatus ?: "未知"}", fontSize = 12.sp, color = TextSecondary)
                        val timeStr = telemetry?.let {
                            SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(it.timestamp * 1000))
                        } ?: "--:--:--"
                        Text("更新時間: $timeStr", fontSize = 12.sp, color = TextSecondary)
                    }
                }
            }

            // 4. 遠端指令控制面板 (Tesla Fleet API 下控)
            Text("雲端遠端控制 (Tesla Fleet API)", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = TextPrimary)
            Card(
                colors = CardDefaults.cardColors(containerColor = CardBackground),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("備用保留電量 (Backup Reserve):", fontSize = 14.sp, color = TextSecondary)
                        Text("${reserveSlider.toInt()}%", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = GridBlue)
                    }

                    Slider(
                        value = reserveSlider,
                        onValueChange = { reserveSlider = it },
                        valueRange = 0f..100f,
                        steps = 19,
                        colors = SliderDefaults.colors(thumbColor = GridBlue, activeTrackColor = GridBlue)
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        Button(
                            onClick = {
                                isSendingControl = true
                                controlActionStatus = "發送保留電量指令中..."
                                coroutineScope.launch {
                                    val res = sendFleetReserve(configRepo.cloudApiUrl, configRepo.siteId, reserveSlider.toInt())
                                    isSendingControl = false
                                    controlActionStatus = if (res.isSuccess) {
                                        "✅ 保留電量 ${reserveSlider.toInt()}% 設定成功"
                                    } else {
                                        "❌ 設定失敗: ${res.exceptionOrNull()?.message}"
                                    }
                                }
                            },
                            enabled = !isSendingControl,
                            colors = ButtonDefaults.buttonColors(containerColor = GridBlue)
                        ) {
                            Text("套用保留電量", color = Color.White)
                        }
                    }

                    HorizontalDivider(color = Color(0xFF333333))

                    Text("儲能運作模式切換:", fontSize = 14.sp, color = TextSecondary)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            modifier = Modifier.weight(1f),
                            onClick = {
                                isSendingControl = true
                                controlActionStatus = "切換至自主模式中..."
                                coroutineScope.launch {
                                    val res = sendFleetMode(configRepo.cloudApiUrl, configRepo.siteId, "autonomous")
                                    isSendingControl = false
                                    controlActionStatus = if (res.isSuccess) "✅ 已切換至「自主排程」模式" else "❌ 切換失敗: ${res.exceptionOrNull()?.message}"
                                }
                            },
                            enabled = !isSendingControl
                        ) {
                            Text("自主運作", fontSize = 12.sp)
                        }

                        OutlinedButton(
                            modifier = Modifier.weight(1f),
                            onClick = {
                                isSendingControl = true
                                controlActionStatus = "切換至自發自用模式中..."
                                coroutineScope.launch {
                                    val res = sendFleetMode(configRepo.cloudApiUrl, configRepo.siteId, "self_consumption")
                                    isSendingControl = false
                                    controlActionStatus = if (res.isSuccess) "✅ 已切換至「自發自用」模式" else "❌ 切換失敗: ${res.exceptionOrNull()?.message}"
                                }
                            },
                            enabled = !isSendingControl
                        ) {
                            Text("自發自用", fontSize = 12.sp)
                        }

                        OutlinedButton(
                            modifier = Modifier.weight(1f),
                            onClick = {
                                isSendingControl = true
                                controlActionStatus = "切換至備用模式中..."
                                coroutineScope.launch {
                                    val res = sendFleetMode(configRepo.cloudApiUrl, configRepo.siteId, "backup")
                                    isSendingControl = false
                                    controlActionStatus = if (res.isSuccess) "✅ 已切換至「純備用」模式" else "❌ 切換失敗: ${res.exceptionOrNull()?.message}"
                                }
                            },
                            enabled = !isSendingControl
                        ) {
                            Text("備用模式", fontSize = 12.sp)
                        }
                    }

                    controlActionStatus?.let { status ->
                        Text(
                            text = status,
                            fontSize = 12.sp,
                            color = if (status.startsWith("✅")) BatteryGreen else Color(0xFFFF8A80)
                        )
                    }
                }
            }

            // 5. 手機保活優化按鈕
            OutlinedButton(
                onClick = onRequestBatteryExemption,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = GridBlue)
            ) {
                Icon(Icons.Default.BatteryAlert, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("略過系統電池優化 (確保手機24H背景不被殺進程)")
            }

            if (telemetry != null && !telemetry!!.isSuccess) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF3E1A1A)),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "TEG 採集提示: ${telemetry!!.errorMsg}",
                        color = Color(0xFFFF8A80),
                        fontSize = 12.sp,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }
        }
    }

    if (showSettingsDialog) {
        SettingsDialog(
            configRepo = configRepo,
            onDismiss = { showSettingsDialog = false }
        )
    }
}

@Composable
fun MetricCard(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    unit: String,
    icon: ImageVector,
    accentColor: Color,
    subtitle: String
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBackground),
        shape = RoundedCornerShape(12.dp),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(title, fontSize = 13.sp, color = TextSecondary)
                Icon(icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(20.dp))
            }
            Spacer(modifier = Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(value, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                Spacer(modifier = Modifier.width(4.dp))
                Text(unit, fontSize = 13.sp, color = TextSecondary, modifier = Modifier.padding(bottom = 3.dp))
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(subtitle, fontSize = 11.sp, color = accentColor)
        }
    }
}

@Composable
fun SettingsDialog(
    configRepo: ConfigRepository,
    onDismiss: () -> Unit
) {
    var siteId by remember { mutableStateOf(configRepo.siteId) }
    var tegHost by remember { mutableStateOf(configRepo.tegHost) }
    var tegPassword by remember { mutableStateOf(configRepo.tegPassword) }
    var tegEmail by remember { mutableStateOf(configRepo.tegEmail) }
    var tegUseSsl by remember { mutableStateOf(configRepo.tegUseSsl) }

    var mqttHost by remember { mutableStateOf(configRepo.mqttHost) }
    var mqttPort by remember { mutableStateOf(configRepo.mqttPort.toString()) }
    var mqttUsername by remember { mutableStateOf(configRepo.mqttUsername) }
    var mqttPassword by remember { mutableStateOf(configRepo.mqttPassword) }
    var mqttUseTls by remember { mutableStateOf(configRepo.mqttUseTls) }
    var pollInterval by remember { mutableStateOf(configRepo.pollIntervalSec.toString()) }
    var autoStartBoot by remember { mutableStateOf(configRepo.autoStartOnBoot) }
    var cloudApiUrl by remember { mutableStateOf(configRepo.cloudApiUrl) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("邊緣端通訊與環境設定") },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("一鍵套用測試/實體環境預設:", fontWeight = FontWeight.Bold, color = BatteryGreen)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    FilledTonalButton(
                        onClick = {
                            tegHost = "192.168.50.177:8675"
                            tegUseSsl = false
                            mqttHost = "broker.emqx.io"
                            mqttPort = "1883"
                            cloudApiUrl = "http://192.168.50.177:8000"
                        },
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 4.dp, vertical = 2.dp)
                    ) {
                        Text("💻 電腦Wi-Fi測試", fontSize = 11.sp)
                    }

                    FilledTonalButton(
                        onClick = {
                            tegHost = "192.168.91.1"
                            tegUseSsl = true
                            mqttHost = "broker.emqx.io"
                            mqttPort = "1883"
                        },
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 4.dp, vertical = 2.dp)
                    ) {
                        Text("🏢 實體TEG直連", fontSize = 11.sp)
                    }

                    FilledTonalButton(
                        onClick = {
                            tegHost = "10.0.2.2:8675"
                            tegUseSsl = false
                            cloudApiUrl = "http://10.0.2.2:8000"
                        },
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 4.dp, vertical = 2.dp)
                    ) {
                        Text("🤖 模擬器", fontSize = 11.sp)
                    }
                }

                HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                Text("Tesla Gateway (TEG) 本地連線", fontWeight = FontWeight.Bold, color = BatteryGreen)
                OutlinedTextField(value = siteId, onValueChange = { siteId = it }, label = { Text("案場識別碼 (Site ID)") })
                OutlinedTextField(value = tegHost, onValueChange = { tegHost = it }, label = { Text("TEG IP 位址/連接埠") })
                OutlinedTextField(
                    value = tegPassword,
                    onValueChange = { tegPassword = it },
                    label = { Text("TEG 密碼 (實體案場請填閘道密碼)") },
                    visualTransformation = PasswordVisualTransformation()
                )
                OutlinedTextField(value = tegEmail, onValueChange = { tegEmail = it }, label = { Text("客戶信箱 (Email)") })
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = tegUseSsl, onCheckedChange = { tegUseSsl = it })
                    Text("使用 HTTPS (實體 TEG 請勾選)")
                }

                HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                Text("雲端 MQTT 伺服器 (MQTTS)", fontWeight = FontWeight.Bold, color = GridBlue)
                OutlinedTextField(value = mqttHost, onValueChange = { mqttHost = it }, label = { Text("MQTT Broker 主機位址") })
                OutlinedTextField(
                    value = mqttPort,
                    onValueChange = { mqttPort = it },
                    label = { Text("連接埠 (一般: 1883 / TLS: 8883)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )
                OutlinedTextField(value = mqttUsername, onValueChange = { mqttUsername = it }, label = { Text("MQTT 使用者名稱 (選填)") })
                OutlinedTextField(
                    value = mqttPassword,
                    onValueChange = { mqttPassword = it },
                    label = { Text("MQTT 密碼 (選填)") },
                    visualTransformation = PasswordVisualTransformation()
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = mqttUseTls, onCheckedChange = { mqttUseTls = it })
                    Text("啟用 MQTTS (TLS 8883 加密)")
                }

                HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                Text("雲端 Fleet API 控制主機", fontWeight = FontWeight.Bold, color = SolarYellow)
                OutlinedTextField(
                    value = cloudApiUrl,
                    onValueChange = { cloudApiUrl = it },
                    label = { Text("雲端 Django 伺服器 URL") }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                OutlinedTextField(
                    value = pollInterval,
                    onValueChange = { pollInterval = it },
                    label = { Text("採集輪詢週期 (秒)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = autoStartBoot, onCheckedChange = { autoStartBoot = it })
                    Text("開機自動啟動前台常駐服務")
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    configRepo.siteId = siteId
                    configRepo.tegHost = tegHost
                    configRepo.tegPassword = tegPassword
                    configRepo.tegEmail = tegEmail
                    configRepo.tegUseSsl = tegUseSsl

                    configRepo.mqttHost = mqttHost
                    configRepo.mqttPort = mqttPort.toIntOrNull() ?: 1883
                    configRepo.mqttUsername = mqttUsername
                    configRepo.mqttPassword = mqttPassword
                    configRepo.mqttUseTls = mqttUseTls

                    configRepo.cloudApiUrl = cloudApiUrl
                    configRepo.pollIntervalSec = pollInterval.toIntOrNull() ?: 3
                    configRepo.autoStartOnBoot = autoStartBoot

                    onDismiss()
                }
            ) {
                Text("儲存設定")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消")
            }
        }
    )
}

suspend fun sendFleetReserve(baseUrl: String, siteId: String, reservePercent: Int): Result<String> = withContext(Dispatchers.IO) {
    try {
        val cleanUrl = baseUrl.trimEnd('/')
        val url = URL("$cleanUrl/api/control/backup-reserve/")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
            doOutput = true
            connectTimeout = 5000
            readTimeout = 5000
        }
        val body = JSONObject().apply {
            put("site_id", siteId)
            put("reserve_percent", reservePercent)
        }
        OutputStreamWriter(conn.outputStream, "UTF-8").use { it.write(body.toString()) }
        val code = conn.responseCode
        val response = if (code in 200..299) {
            conn.inputStream.bufferedReader().use { it.readText() }
        } else {
            conn.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
        }
        if (code in 200..299) Result.success(response) else Result.failure(Exception("HTTP $code: $response"))
    } catch (e: Exception) {
        Result.failure(e)
    }
}

suspend fun sendFleetMode(baseUrl: String, siteId: String, mode: String): Result<String> = withContext(Dispatchers.IO) {
    try {
        val cleanUrl = baseUrl.trimEnd('/')
        val url = URL("$cleanUrl/api/control/operation-mode/")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
            doOutput = true
            connectTimeout = 5000
            readTimeout = 5000
        }
        val body = JSONObject().apply {
            put("site_id", siteId)
            put("mode", mode)
        }
        OutputStreamWriter(conn.outputStream, "UTF-8").use { it.write(body.toString()) }
        val code = conn.responseCode
        val response = if (code in 200..299) {
            conn.inputStream.bufferedReader().use { it.readText() }
        } else {
            conn.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
        }
        if (code in 200..299) Result.success(response) else Result.failure(Exception("HTTP $code: $response"))
    } catch (e: Exception) {
        Result.failure(e)
    }
}
