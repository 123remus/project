"""
MQTT Ingestion Worker (資料攝取常駐行程)
對應架構圖中「資料攝取層」：
1. 訂閱 MQTT Broker 遙測串流 (Topic: site/+/telemetry, site/+/status)
2. 雙寫入管線 (Dual-Write Pipeline):
   - Update Latest State: 寫入 Redis 快取 (Hash: site:{site_id}:latest)
   - Batch Insert: 批次寫入 TimescaleDB / Django ORM
3. 透過 Django Channels 轉發即時 WebSocket 事件至 Web Dashboard
"""

import os
import sys
import json
import time
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path

# 將 Django 根目錄加入 Python 路徑
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ems_core.settings')

import django
django.setup()

import paho.mqtt.client as mqtt
import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.sites.models import Site
from apps.telemetry.models import TelemetryRecord

# 組態設定 (預設與 Android 端一致使用 broker.emqx.io 公共 Broker)
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'broker.emqx.io')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

BATCH_FLUSH_INTERVAL = 1.0  # 批次寫入間隔 (1秒即時同步)
BATCH_SIZE_LIMIT = 20       # 批次寫入筆數閥值

class MqttIngestionWorker:
    def __init__(self):
        self.running = True
        self.buffer_lock = threading.Lock()
        self.telemetry_buffer = []
        
        # 初始化 Redis 連線 (快速偵測 0.3s，避免阻塞)
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                decode_responses=True, 
                socket_connect_timeout=0.3, 
                socket_timeout=0.3
            )
            self.redis_client.ping()
            self.redis_available = True
            print(f"[+] Redis 連線成功: {REDIS_HOST}:{REDIS_PORT}", flush=True)
        except Exception:
            self.redis_available = False
            print(f"[!] Redis 未就緒，將以本機 Channel Layer 與資料庫直接運作", flush=True)

        # 取得 Channels 傳輸層
        try:
            self.channel_layer = get_channel_layer()
        except Exception:
            self.channel_layer = None

        # 統計計數器
        self.stats = {
            "received": 0,
            "saved": 0,
            "start_time": time.time()
        }

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        # 相容 Paho MQTT v1 與 v2 ReasonCode
        is_ok = (rc == 0) or (hasattr(rc, 'is_failure') and not rc.is_failure)
        if is_ok:
            print(f"[+] 成功連線至 MQTT Broker ({MQTT_BROKER_HOST}:{MQTT_BROKER_PORT})", flush=True)
            client.subscribe("site/+/telemetry", qos=1)
            client.subscribe("site/+/status", qos=1)
            print("[*] 正在監聽主題: site/+/telemetry, site/+/status", flush=True)
        else:
            print(f"[-] MQTT 連線失敗，代碼: {rc}", flush=True)

    def on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode('utf-8', errors='ignore')

        try:
            data = json.loads(payload_str)
        except Exception:
            print(f"[!] 無效的 JSON 封包: {payload_str}")
            return

        self.stats["received"] += 1

        if topic.endswith("/telemetry"):
            self.process_telemetry(data)
        elif topic.endswith("/status"):
            self.process_status(data)

    def process_telemetry(self, data):
        site_id = data.get("site_id", "site_01")
        timestamp = data.get("timestamp", time.time())
        record_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # 1. 寫入 Redis 快取 (Update Latest State)
        if self.redis_available:
            try:
                self.redis_client.set(f"site:{site_id}:latest", json.dumps(data), ex=300)
            except Exception as e:
                print(f"[!] 寫入 Redis 失敗: {e}")

        # 2. 廣播至 Django Channels WebSocket 群組
        if self.channel_layer:
            try:
                async_to_sync(self.channel_layer.group_send)(
                    f"telemetry_{site_id}",
                    {
                        "type": "telemetry_update",
                        "data": data
                    }
                )
            except Exception:
                pass

        # 3. 加入批次寫入緩衝區 (Batch Insert -> TimescaleDB)
        with self.buffer_lock:
            self.telemetry_buffer.append((site_id, record_time, data))

    def process_status(self, data):
        site_id = data.get("site_id", "site_01")
        status_val = data.get("status", "unknown")
        print(f"[*] 收到案場狀態通知: 案場 {site_id} 目前狀態 -> {status_val}")
        if self.redis_available:
            try:
                self.redis_client.set(f"site:{site_id}:status", status_val, ex=600)
            except Exception:
                pass

    def flush_loop(self):
        """背景定時批次寫入資料庫"""
        last_flush = time.time()
        while self.running:
            time.sleep(0.5)
            now = time.time()
            need_flush = False

            with self.buffer_lock:
                if len(self.telemetry_buffer) >= BATCH_SIZE_LIMIT or (len(self.telemetry_buffer) > 0 and now - last_flush >= BATCH_FLUSH_INTERVAL):
                    records_to_save = list(self.telemetry_buffer)
                    self.telemetry_buffer.clear()
                    need_flush = True

            if need_flush and records_to_save:
                self.batch_insert_db(records_to_save)
                last_flush = time.time()

    def batch_insert_db(self, records):
        """執行資料庫批次寫入"""
        try:
            # 確保涉及的案場記錄存在
            site_ids = set(r[0] for r in records)
            for sid in site_ids:
                Site.objects.get_or_create(site_id=sid, defaults={"name": f"案場 {sid}"})

            objs = []
            for site_id, record_time, data in records:
                objs.append(TelemetryRecord(
                    site_id=site_id,
                    time=record_time,
                    solar_kw=data.get("solar_kw", 0.0),
                    grid_kw=data.get("grid_kw", 0.0),
                    battery_kw=data.get("battery_kw", 0.0),
                    home_kw=data.get("home_kw", 0.0),
                    soc_pct=data.get("soc_pct", 0.0),
                    grid_status=data.get("grid_status", "Connected"),
                    raw_payload=data
                ))

            TelemetryRecord.objects.bulk_create(objs, batch_size=100)
            self.stats["saved"] += len(objs)
            print(f"[DB] 批次寫入 {len(objs)} 筆遙測紀錄至資料庫 (累計入庫: {self.stats['saved']})", flush=True)

        except Exception as e:
            print(f"[!] 批次入庫異常: {e}", flush=True)

    def run(self):
        # 啟動批次持久化執行緒
        flush_thread = threading.Thread(target=self.flush_loop, daemon=True)
        flush_thread.start()

        # 啟動 MQTT 客戶端
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, 'CallbackAPIVersion') else None, client_id="ems-cloud-ingestion-worker")
        client.on_connect = self.on_mqtt_connect
        client.on_message = self.on_mqtt_message

        print("=" * 65, flush=True)
        print("  Tesla EMS 雲端資料攝取 Worker 已啟動 (Ingestion Layer)", flush=True)
        print(f"  MQTT Broker : {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}", flush=True)
        print(f"  Redis Cache : {REDIS_HOST}:{REDIS_PORT}", flush=True)
        print("  雙寫管線    : TimescaleDB 批次寫入 + Redis 秒級即時快取", flush=True)
        print("=" * 65, flush=True)

        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            client.loop_forever()
        except KeyboardInterrupt:
            print("\n[*] 正在關閉 Ingestion Worker...", flush=True)
            self.running = False
            client.disconnect()
            flush_thread.join(timeout=2)
            print("[*] Worker 安全關閉完成。", flush=True)

if __name__ == '__main__':
    worker = MqttIngestionWorker()
    worker.run()
