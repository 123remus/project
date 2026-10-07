import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.sites.models import Site
from .models import ControlLog
from .tesla_client import TeslaFleetApiClient

logger = logging.getLogger(__name__)
tesla_client = TeslaFleetApiClient()

class SetBackupReserveView(APIView):
    """
    設定備用保留電量 (Backup Reserve Percent)
    POST /api/control/backup-reserve/
    {
        "site_id": "site_01",
        "reserve_percent": 30
    }
    """
    def post(self, request):
        site_id = request.data.get('site_id')
        reserve_percent = request.data.get('reserve_percent')

        if not site_id or reserve_percent is None:
            return Response({"error": "缺少 site_id 或 reserve_percent 參數"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reserve_percent = int(reserve_percent)
            if not (0 <= reserve_percent <= 100):
                raise ValueError()
        except ValueError:
            return Response({"error": "reserve_percent 必須介於 0 至 100 之間"}, status=status.HTTP_400_BAD_REQUEST)

        # 確保案場存在
        Site.objects.get_or_create(site_id=site_id, defaults={"name": f"案場 {site_id}"})

        # 記錄稽核日誌
        log = ControlLog.objects.create(
            site_id=site_id,
            command_type='backup_reserve',
            parameters={'reserve_percent': reserve_percent},
            status='PENDING'
        )

        try:
            result = tesla_client.set_backup_reserve(site_id, reserve_percent)
            log.status = 'SUCCESS'
            log.tesla_command_id = result.get('command_id', '')
            log.tesla_response = result.get('response', {})
            log.save()
            return Response({
                "status": "success",
                "message": result.get("message", "設定成功"),
                "log_id": log.id,
                "command_id": log.tesla_command_id
            })
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            log.save()
            return Response({"status": "failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SetOperationModeView(APIView):
    """
    設定儲能運作模式 (Operation Mode)
    POST /api/control/operation-mode/
    {
        "site_id": "site_01",
        "mode": "self_consumption" | "autonomous" | "backup"
    }
    """
    def post(self, request):
        site_id = request.data.get('site_id')
        mode = request.data.get('mode')

        if not site_id or not mode:
            return Response({"error": "缺少 site_id 或 mode 參數"}, status=status.HTTP_400_BAD_REQUEST)

        valid_modes = ['self_consumption', 'autonomous', 'backup']
        if mode not in valid_modes:
            return Response({"error": f"mode 必須為 {valid_modes} 之一"}, status=status.HTTP_400_BAD_REQUEST)

        Site.objects.get_or_create(site_id=site_id, defaults={"name": f"案場 {site_id}"})

        log = ControlLog.objects.create(
            site_id=site_id,
            command_type='operation_mode',
            parameters={'mode': mode},
            status='PENDING'
        )

        try:
            result = tesla_client.set_operation_mode(site_id, mode)
            log.status = 'SUCCESS'
            log.tesla_command_id = result.get('command_id', '')
            log.tesla_response = result.get('response', {})
            log.save()
            return Response({
                "status": "success",
                "message": result.get("message", "模式切換成功"),
                "log_id": log.id,
                "command_id": log.tesla_command_id
            })
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            log.save()
            return Response({"status": "failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ControlLogListView(APIView):
    """
    查詢案場控制歷史稽核紀錄
    GET /api/control/logs/?site_id=site_01
    """
    def get(self, request):
        site_id = request.query_params.get('site_id')
        qs = ControlLog.objects.all()
        if site_id:
            qs = qs.filter(site_id=site_id)
        qs = qs[:50]

        logs = []
        for item in qs:
            logs.append({
                "id": item.id,
                "site_id": item.site_id,
                "command_type": item.command_type,
                "parameters": item.parameters,
                "status": item.status,
                "tesla_command_id": item.tesla_command_id,
                "error_message": item.error_message,
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return Response({"logs": logs})
