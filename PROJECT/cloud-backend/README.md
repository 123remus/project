# Tesla EMS 雲端平台後端與資料攝取層 (Cloud Infrastructure)

本目錄包含架構圖中的：
- **Web 服務層 (Django)**：Django 5 + DRF + Django Channels (ASGI / WebSockets) + Tesla Fleet API 控制器
- **資料攝取層 (Ingestion Layer)**：`workers/mqtt_ingestion_daemon.py`
- **資料儲存層**：支援 TimescaleDB (PostgreSQL 16) 與 Redis (支援本機 SQLite 與快取自動相容模式)
- **監控與控制前端 (Web Dashboard)**：內建於 `templates/dashboard/index.html`，具備動態能源流向圖與控制面板

---

## 目錄結構

```text
cloud-backend/
├── ems_core/                            # Django 核心配置 (ASGI/WSGI/Settings/URLs)
│   ├── settings.py
│   ├── asgi.py                          # 整合 Daphne 與 WebSocket 路由
│   └── urls.py
├── apps/
│   ├── sites/                           # 案場基本資料管理
│   ├── telemetry/                       # 遙測數據模型、REST API、WebSocket Consumer
│   └── fleet_control/                   # Tesla Fleet API 控制器 (OAuth 2.0、指令下發與稽核)
├── workers/
│   └── mqtt_ingestion_daemon.py         # 訂閱 MQTT 串流並雙寫入 TimescaleDB 與 Redis
├── templates/
│   └── dashboard/
│       └── index.html                   # 監控與控制前端儀表板 (動態拓撲圖、SoC 儀表、控制滑桿)
├── manage.py
└── requirements.txt
```

---

## 快速啟動指南

### 1. 啟動 Django 後端與 Web 儀表板
```bash
python manage.py runserver 0.0.0.0:8000
```
瀏覽器開啟：`http://127.0.0.1:8000/` 即可進入即時能源儀表板！

### 2. 啟動資料攝取 Worker (接收邊緣端 MQTT 上傳)
開啟另一個終端機：
```bash
python workers/mqtt_ingestion_daemon.py
```
Worker 將自動訂閱 `site/+/telemetry`，將邊緣端 Android 上傳的數據：
1. **即時寫入 Redis**（或本機 Channel Layer）並透過 WebSocket 推播至所有已打開網頁的瀏覽器。
2. **批次聚合寫入 TimescaleDB**。

---

## API 端點清單

### 遙測查詢端點
- `GET /api/telemetry/latest/<site_id>/`：讀取當前快取狀態
- `GET /api/telemetry/history/<site_id>/?hours=24`：讀取歷史時間序列圖表數據
- `GET /api/telemetry/summary/<site_id>/`：今日累計發電量、用電量與進出電網度數

### Tesla Fleet API 雲端控制端點
- `POST /api/control/backup-reserve/`
  ```json
  {
    "site_id": "site_01",
    "reserve_percent": 30
  }
  ```
- `POST /api/control/operation-mode/`
  ```json
  {
    "site_id": "site_01",
    "mode": "self_consumption" // 或 "autonomous", "backup"
  }
  ```
- `GET /api/control/logs/?site_id=site_01`：查詢控制歷史紀錄與 Tesla 官方雲端回應

### WebSocket 即時串流端點
- `ws://127.0.0.1:8000/ws/telemetry/<site_id>/`
