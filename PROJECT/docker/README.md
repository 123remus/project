# EMS 雲端基礎設施部署說明

本目錄提供使用 Docker Compose 一鍵啟動的雲端平台基礎設施，包含：
- **EMQX 5.x**：高併發物聯網 MQTT Broker (連接埠: 1883, 8883 MQTTS, 18083 儀表板)
- **TimescaleDB**：PostgreSQL 16 + 時間序列擴充 (連接埠: 5432)
- **Redis 7**：快取與即時狀態通道 (連接埠: 6379)

---

## 啟動方式

確保 Docker Desktop 已開啟，於本目錄下執行：

```bash
docker-compose up -d
```

### 檢查服務健康狀態
```bash
docker-compose ps
```

### 登入 EMQX 儀表板
- 網址：`http://localhost:18083`
- 帳號：`admin`
- 密碼：`public` (首次登入可修改)

### 停止服務
```bash
docker-compose down
```
*(若要完全清除資料庫持久化磁碟區，可加上 `-v` 參數)*
