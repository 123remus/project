# Mock 模擬測試環境使用說明

本目錄提供在沒有實體 Tesla Powerwall 2 Gateway (TEG) 硬體設備時的本機端完整模擬環境。

---

## 包含組件

1. **`mock_teg_server.py`**：
   - 模擬 Tesla Powerwall 2 Gateway 核心 API（包含 `/api/login/Basic`、`/api/meters/aggregates`、`/api/system_status/soe` 等）。
   - 內建動態功率波動演算法（模擬白天太陽能發電、家庭用電尖峰、電池充放電與電網平衡回售）。
   - 支援 HTTP（預設連接埠 `8675`）。

2. **`test_edge_collector.py`**：
   - 獨立的 Python 採集邏輯測試腳本。
   - 可直接在電腦上測試對接 `mock_teg_server.py` 或實體 TEG，免裝 Android 即可先驗證資料採集與 JSON 格式。

3. **`test_mqtt_subscriber.py`**：
   - MQTT 訂閱測試端，自動訂閱 `site/+/telemetry` 與 `site/+/status`。
   - 當 Android App 上傳數據時，會以格式化表格即時印出太陽能、電網、電池功率與 SoC。

---

## 快速啟動指南

### 步驟 1：啟動 Mock TEG 伺服器
```bash
python mock_teg_server.py 8675
```
啟動後會顯示：
```
[*] Mock Tesla Powerwall 2 Gateway (TEG) 已啟動
[*] 監聽位址: http://127.0.0.1:8675
```

### 步驟 2：測試 Python 採集端
開啟另一個終端機視窗：
```bash
python test_edge_collector.py 127.0.0.1:8675
```
您將看到即時採集的電表讀數與 SoC 數據以 2 秒間隔滾動印出。

### 步驟 3：在 Android App / 模擬器中連線測試
- 若使用 **Android 實體機**：請將手機與電腦連至同一 Wi-Fi，在 Android App 設定頁將 TEG IP 填入電腦的區域網路 IP（例如 `http://192.168.1.100:8675`）。
- 若使用 **Android Studio 模擬器**：TEG IP 請填入 `http://10.0.2.2:8675`（`10.0.2.2` 是 Android 模擬器指向主機電腦 localhost 的專用別名）。
