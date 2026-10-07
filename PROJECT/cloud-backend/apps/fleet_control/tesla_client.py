import time
import uuid
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class TeslaFleetApiClient:
    """
    Tesla Fleet API 控制器 (對應架構圖中 Fleet API Controller)
    負責 OAuth 2.0 Partner Token 換發與向 Tesla 官方雲端發送 HTTPS REST 控制指令
    """
    def __init__(self):
        self.config = settings.TESLA_FLEET_CONFIG
        self.client_id = self.config.get('CLIENT_ID')
        self.client_secret = self.config.get('CLIENT_SECRET')
        self.base_url = self.config.get('BASE_URL').rstrip('/')
        self.token_url = self.config.get('TOKEN_URL')
        self.mock_mode = self.config.get('MOCK_MODE', True)
        self._cached_token = None
        self._token_expires_at = 0

    def get_access_token(self) -> str:
        """取得有效之 OAuth 2.0 Partner Token"""
        if self.mock_mode:
            return "mock_tesla_partner_bearer_token_xyz"

        now = time.time()
        if self._cached_token and now < self._token_expires_at - 60:
            return self._cached_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid energy_device_data energy_cmds"
        }
        resp = requests.post(self.token_url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._cached_token = data.get("access_token")
        self._token_expires_at = now + data.get("expires_in", 3600)
        return self._cached_token

    def set_backup_reserve(self, site_id: str, reserve_percent: int) -> dict:
        """
        向 Tesla 官方雲端發送設定備用電量指令 (HTTPS REST)
        端點: POST /api/1/energy_sites/{site_id}/backup
        """
        if self.mock_mode:
            time.sleep(0.3)  # 模擬真實雲端網路延遲
            return {
                "success": True,
                "command_id": f"cmd_{uuid.uuid4().hex[:12]}",
                "message": f"Tesla 官方雲端已接收指令: 案場 {site_id} 備用保留電量已設為 {reserve_percent}%",
                "response": {
                    "code": 201,
                    "updated_backup_reserve_percent": reserve_percent
                }
            }

        token = self.get_access_token()
        url = f"{self.base_url}/api/1/energy_sites/{site_id}/backup"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {"backup_reserve_percent": reserve_percent}
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return {
            "success": True,
            "command_id": resp.headers.get("x-txid", f"cmd_{uuid.uuid4().hex[:12]}"),
            "response": resp.json()
        }

    def set_operation_mode(self, site_id: str, mode: str) -> dict:
        """
        向 Tesla 官方雲端發送切換運作模式指令 (HTTPS REST)
        端點: POST /api/1/energy_sites/{site_id}/operation
        mode 可選值: 'self_consumption' (自發自用), 'autonomous' (時間電價平衡), 'backup' (純備用)
        """
        valid_modes = ['self_consumption', 'autonomous', 'backup']
        if mode not in valid_modes:
            raise ValueError(f"無效的運作模式: {mode}，必須為 {valid_modes} 之一")

        if self.mock_mode:
            time.sleep(0.3)
            mode_names = {
                'self_consumption': '自發自用 (Self-Consumption)',
                'autonomous': '時間電價平衡 (Autonomous)',
                'backup': '純備用電源 (Backup)'
            }
            return {
                "success": True,
                "command_id": f"cmd_{uuid.uuid4().hex[:12]}",
                "message": f"Tesla 官方雲端已接收指令: 案場 {site_id} 運作模式已切換為 {mode_names.get(mode, mode)}",
                "response": {
                    "code": 201,
                    "default_real_mode": mode
                }
            }

        token = self.get_access_token()
        url = f"{self.base_url}/api/1/energy_sites/{site_id}/operation"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {"default_real_mode": mode}
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return {
            "success": True,
            "command_id": resp.headers.get("x-txid", f"cmd_{uuid.uuid4().hex[:12]}"),
            "response": resp.json()
        }
