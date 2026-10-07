# Tesla Powerwall 邊緣端 Android Gateway (EMS Edge)

本專案為架構圖中現場儲能案場 (Edge Layer) 的 Android 邊緣端應用程式。
負責透過區域網路以 HTTPS / Token 認證讀取 Tesla Powerwall 2 Gateway (TEG) 電表與電池數據，並透過 MQTTS (TLS 8883) 上傳至自建雲端平台。

---

## 核心技術與特色

1. **常駐前台服務 (Foreground Service)**：
   - 使用 `FOREGROUND_SERVICE_DATA_SYNC` 權限與常駐狀態列通知。
   - 獲取系統 `PARTIAL_WAKE_LOCK`，防止 Android 在滅屏時進入休眠而中斷採集。
   - 支援 `BOOT_COMPLETED` 開機自啟動，適合案場專用平板或電視盒無人值守運作。
   - 內建一鍵申請豁免系統電池優化 (`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`)。

2. **Chaquopy 內嵌 Python Runtime (`pypowerwall`)**：
   - 透過 Chaquopy 在 Android 內部直接執行 Python 3.10 環境。
   - 使用 `pypowerwall` 與相容 REST API 封裝模組 (`teg_collector.py`)。
   - 具備自動登入 Token 快取機制與 SSL 自簽名憑證寬容性。

3. **Paho MQTT 客戶端**：
   - 支援標準 TCP (1883) 與加密 MQTTS (TLS 8883)。
   - 發布主題：`site/{site_id}/telemetry`（QoS 1）。
   - 遺囑主題 (LWT)：`site/{site_id}/status`，若設備非預期斷線將自動通知雲端。

4. **Jetpack Compose 現代化介面**：
   - 即時儀表卡片：太陽能發電 (kW)、電網進出 (kW)、電池儲能充放 (kW)、家庭負載 (kW)。
   - 電池可用電量 (SoC %) 進度條與狀態指示。
   - 案場參數設定對話框（隨時調整 TEG IP、密碼、MQTT Broker、輪詢頻率等）。

---

## 如何在 Android Studio 中開啟與編譯

### 需求
- Android Studio Hedgehog (2023.1.1) 或更新版本
- JDK 17
- Android SDK 34 (API 34)
- 實體 Android 手機/平板 (Android 8.0 / API 26 以上) 或 Android Studio 模擬器

### 步驟
1. 開啟 Android Studio，選擇 **Open**，選擇 `edge-android` 資料夾。
2. 等待 Gradle Sync 完成（Chaquopy 會自動下載對應平台之 Python 執行時期與 pip 依賴套件）。
3. 連接 Android 裝置或啟動模擬器。
4. 點擊 **Run 'app'** 即可編譯安裝。

---

## 本機模擬測試教學 (搭配 mock-env)

若目前沒有實體 Tesla Powerwall 2 閘道器，請按照以下步驟進行本地聯調：

### 1. 啟動 Mock TEG 伺服器
在專案根目錄開啟終端機：
```bash
python mock-env/mock_teg_server.py 8675
```

### 2. 設定 Android App
- **使用 Android Studio 模擬器時**：
  - 點擊右上角設定按鈕 ⚙️
  - **TEG IP 位址** 填入：`10.0.2.2:8675`（`10.0.2.2` 為模擬器連接本機電腦之 IP）
  - **使用 HTTPS**：取消勾選（Mock 伺服器使用 HTTP）
  - **MQTT Broker**：可填入公共 Broker `broker.emqx.io`（連接埠 1883）或本機 Broker
  - 點擊「儲存設定」
- **使用實體 Android 裝置時**：
  - 請將手機與電腦連至同一個 Wi-Fi 網路。
  - 將 TEG IP 填入電腦的區域網路 IP（例如 `192.168.1.100:8675`）。

### 3. 啟動常駐服務
- 在 App 首頁點擊 **「啟動服務」**。
- 您將在 App 畫面上看到太陽能、電網、電池與家庭用電的動態數值開始滾動更新。
- 狀態列將出現常駐通知。

### 4. 驗證 MQTT 訊息接收
在電腦另開終端機執行：
```bash
python mock-env/test_mqtt_subscriber.py broker.emqx.io 1883
```
即可看到 Android App 即時發布的 `site/site_01/telemetry` 封包！
