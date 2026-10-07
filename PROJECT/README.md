# Tesla Powerwall 能源管理系統 (EMS) 完整全端專案

本專案完整實現架構圖中的四大核心領域：

```text
[現場案場 TEG] ──(Local LAN/HTTPs)──> [Android 邊緣網關 (Chaquopy + pypowerwall)]
                                                    │
                                                    ▼ (MQTTS TLS 8883)
                                          [MQTT Broker (EMQX)]
                                                    │
                                          [Ingestion Worker]
                                           /              \
                                          ▼                ▼
                                 [TimescaleDB]        [Redis Cache]
                                          \                /
                                           ▼              ▼
                                      [Django 後端 (DRF / Channels)]
                                           │              │
                    (Command & Control)    ▼              ▼ (REST / WebSocket)
                         [Tesla Fleet API]       [Web 監控儀表板]
```

---

## 模組對照清單

| 架構節點 | 目錄位置 | 技術規格與說明 |
| :--- | :--- | :--- |
| **1. 現場儲能邊緣端** | `edge-android/` | Android 14+ 相容、常駐前台服務 (`TegForegroundService`)、WakeLock 保活、開機自啟 (`BootReceiver`)、Chaquopy 內嵌 Python (`pypowerwall`)、Paho MQTT (MQTTS TLS 8883 / QoS 1 / LWT)、Jetpack Compose 介面。 |
| **2. 資料攝取與儲存層** | `cloud-backend/workers/`<br>`docker/` | `mqtt_ingestion_daemon.py`（訂閱 MQTT 串流、雙寫入 Redis 與 TimescaleDB 批次入庫）、EMQX 5.x、TimescaleDB (Hypertable + 30天壓縮 + 連續聚合)、Redis 7。 |
| **3. Web 服務層** | `cloud-backend/` | Django 5 + DRF + Django Channels (ASGI WebSockets) + Tesla Fleet API 控制器（OAuth 2.0 Partner 認證、指令簽名下發、控制稽核日誌）。 |
| **4. 監控與控制前端** | `cloud-backend/templates/` | 即時 Web 儀表板：動態能源流向拓撲圖 (Solar/Grid/Battery/Home)、電池可用電量 (SoC %) 進度儀表、Tesla Fleet API 遠端控制滑桿與模式切換按鈕、Chart.js 歷史時序趨勢分析。 |
| **輔助工具** | `mock-env/` | Mock Tesla Powerwall 2 閘道器伺服器 (`mock_teg_server.py`)、MQTT 訂閱測試端 (`test_mqtt_subscriber.py`)、本地採集測試腳本 (`test_edge_collector.py`)。 |

---

## 🚀 全系統一鍵聯調測試步驟

### 第一步：啟動 Mock TEG 閘道器 (現場模擬)
```bash
python mock-env/mock_teg_server.py 8675
```
*(提供動態太陽能發電曲線與即時電池充放電電表)*

### 第二步：啟動 Django 後端與 Web 儀表板
```bash
cd cloud-backend
python manage.py runserver 0.0.0.0:8000
```
瀏覽器開啟：`http://127.0.0.1:8000/`，即可看到即時動態拓撲圖與控制介面。

### 第三步：啟動雲端 Ingestion Worker (若有啟動本機/公共 MQTT Broker)
```bash
cd cloud-backend
python workers/mqtt_ingestion_daemon.py
```

### 第四步：啟動 Android 邊緣端網關 App
在 Android Studio 中開啟 `edge-android/`，點選 Run 安裝至手機或模擬器，點擊「啟動服務」，數據將由邊緣端採集 ➔ MQTT ➔ Ingestion Worker ➔ Redis/TimescaleDB ➔ Web 儀表板動態呈現！
