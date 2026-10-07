import json
import logging
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import TelemetryRecord

logger = logging.getLogger(__name__)

class TelemetryConsumer(AsyncWebsocketConsumer):
    """
    即時遙測 WebSocket Consumer (對應架構圖中 Web Dashboard 與 Channels 連線)
    前端連線路徑: /ws/telemetry/<site_id>/
    """
    async def connect(self):
        self.site_id = self.scope['url_route']['kwargs']['site_id']
        self.group_name = f"telemetry_{self.site_id}"

        # 加入群組
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # 連線建立後立即發送最新快取數據
        latest_data = await self.get_latest_data(self.site_id)
        if latest_data:
            await self.send(text_data=json.dumps({
                "type": "initial_state",
                "data": latest_data
            }))

    async def disconnect(self, close_code):
        # 退出群組
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # 前端若主動 ping 或請求刷新
        try:
            payload = json.loads(text_data)
            if payload.get("action") == "refresh":
                latest = await self.get_latest_data(self.site_id)
                if latest:
                    await self.send(text_data=json.dumps({
                        "type": "latest_update",
                        "data": latest
                    }))
        except Exception:
            pass

    async def telemetry_update(self, event):
        """
        接收 Ingestion Worker 透過 Channel Layer 廣播的即時遙測事件
        """
        await self.send(text_data=json.dumps({
            "type": "telemetry_update",
            "data": event["data"]
        }))

    @sync_to_async
    def get_latest_data(self, site_id):
        # 1. 僅在明確啟用 Redis 且連線成功時嘗試讀取 (0.2s 逾時)
        if getattr(settings, 'USE_REDIS_CHANNEL', False):
            try:
                r = redis.Redis(
                    host=settings.REDIS_HOST, 
                    port=settings.REDIS_PORT, 
                    decode_responses=True, 
                    socket_connect_timeout=0.2, 
                    socket_timeout=0.2
                )
                raw = r.get(f"site:{site_id}:latest")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

        # 2. 直接由資料庫取得最新一筆遙測紀錄
        try:
            record = TelemetryRecord.objects.filter(site_id=site_id).order_by('-time').first()
            if record:
                return {
                    "site_id": record.site_id,
                    "timestamp": int(record.time.timestamp()),
                    "solar_kw": record.solar_kw,
                    "grid_kw": record.grid_kw,
                    "battery_kw": record.battery_kw,
                    "home_kw": record.home_kw,
                    "soc_pct": record.soc_pct,
                    "grid_status": record.grid_status,
                }
        except Exception as e:
            logger.error(f"Error fetching latest telemetry: {e}")

        return None
