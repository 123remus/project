import json
import redis
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.sites.models import Site
from .models import TelemetryRecord

class DashboardView(TemplateView):
    """
    監控與控制前端儀表板 View (Point 4)
    """
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites = list(Site.objects.filter(is_active=True).values('site_id', 'name', 'teg_ip', 'battery_capacity_kwh'))
        if not sites:
            # 若無案場自動給出範例案場
            sites = [
                {"site_id": "site_01", "name": "案場 A (Site 1 - 台北示範案場)", "teg_ip": "192.168.1.101", "battery_capacity_kwh": 13.5},
                {"site_id": "site_02", "name": "案場 B (Site 2 - 新竹儲能案場)", "teg_ip": "192.168.1.102", "battery_capacity_kwh": 27.0}
            ]
        context['sites'] = sites
        context['default_site_id'] = sites[0]['site_id'] if sites else "site_01"
        return context

class TelemetryLatestView(APIView):
    """
    讀取當前最新快取 (對應架構圖：讀取當前快取 -> Redis Cache)
    """
    def get(self, request, site_id):
        # 1. 僅在啟用 Redis 時嘗試由快取讀取
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
                    data = json.loads(raw)
                    data['source'] = 'redis_cache'
                    return Response(data)
            except Exception:
                pass

        # 2. 回退至資料庫查詢最新一筆
        record = TelemetryRecord.objects.filter(site_id=site_id).order_by('-time').first()
        if record:
            return Response({
                "site_id": record.site_id,
                "timestamp": int(record.time.timestamp()),
                "solar_kw": record.solar_kw,
                "grid_kw": record.grid_kw,
                "battery_kw": record.battery_kw,
                "home_kw": record.home_kw,
                "soc_pct": record.soc_pct,
                "grid_status": record.grid_status,
                "source": "database"
            })

        return Response({
            "site_id": site_id,
            "timestamp": int(timezone.now().timestamp()),
            "solar_kw": 0.0,
            "grid_kw": 0.0,
            "battery_kw": 0.0,
            "home_kw": 0.0,
            "soc_pct": 0.0,
            "grid_status": "No Data",
            "source": "empty"
        })

class TelemetryHistoryView(APIView):
    """
    讀取歷史趨勢/匯總 (對應架構圖：讀取歷史趨勢/匯總 -> TimescaleDB)
    """
    def get(self, request, site_id):
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)

        records = TelemetryRecord.objects.filter(
            site_id=site_id,
            time__gte=start_time
        ).order_by('time')[:500]

        data = []
        for r in records:
            data.append({
                "time": r.time.strftime("%H:%M:%S" if hours <= 24 else "%m/%d %H:%M"),
                "solar_kw": r.solar_kw,
                "grid_kw": r.grid_kw,
                "battery_kw": r.battery_kw,
                "home_kw": r.home_kw,
                "soc_pct": r.soc_pct
            })

        return Response({
            "site_id": site_id,
            "points_count": len(data),
            "data": data
        })

class TelemetrySummaryView(APIView):
    """
    取得今日累積統計數據 (發電量 kWh、用電量 kWh、進出電網等)
    """
    def get(self, request, site_id):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        records = TelemetryRecord.objects.filter(
            site_id=site_id,
            time__gte=today_start
        )

        # 簡易時序積分估算能源 (kWh)
        solar_kwh = sum(r.solar_kw for r in records) * (3.0 / 3600.0) if records.exists() else 0.0
        grid_import_kwh = sum(max(0.0, r.grid_kw) for r in records) * (3.0 / 3600.0) if records.exists() else 0.0
        grid_export_kwh = sum(abs(min(0.0, r.grid_kw)) for r in records) * (3.0 / 3600.0) if records.exists() else 0.0

        return Response({
            "site_id": site_id,
            "today_solar_kwh": round(solar_kwh, 2),
            "today_grid_import_kwh": round(grid_import_kwh, 2),
            "today_grid_export_kwh": round(grid_export_kwh, 2),
            "records_analyzed": records.count()
        })
