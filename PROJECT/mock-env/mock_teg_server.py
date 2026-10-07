"""
Mock Tesla Powerwall 2 Gateway (TEG) Server
模擬 Tesla Powerwall 2 閘道器本地 API 伺服器
提供 /api/login/Basic, /api/meters/aggregates, /api/system_status/soe, /api/sitemaster 等標準端點
內建即時功率動態波動模擬 (太陽能發電、家庭負載、電網回售/吸納、電池充放電)
"""

import http.server
import json
import math
import ssl
import sys
import time
from urllib.parse import urlparse

PORT = 8675
ENABLE_SSL = False  # 可設定為 True 並搭配 self-signed cert

class MockTegHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        content = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Set-Cookie', 'AuthCookie=mock_teg_session_token_12345; Path=/; HttpOnly')
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        
        # 登入認證端點 (支援 Basic / Installer / Customer)
        if parsed.path.startswith('/api/login'):
            response_data = {
                "email": "customer@example.com",
                "firstname": "Mock",
                "lastname": "Customer",
                "roles": ["Customer"],
                "token": "mock_teg_jwt_token_abcdef1234567890",
                "loginTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._send_json(response_data, 200)
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        now_sec = time.time()

        # 動態模擬數值 (以正弦波與隨機雜訊模擬真實電網與太陽能起伏)
        t = now_sec / 10.0
        # 太陽能 (瓦特): 白天正值，加入波動
        solar_w = max(0.0, round(4500 + 1500 * math.sin(t * 0.3) + 200 * math.cos(t * 1.5), 1))
        # 家庭負載 (瓦特): 隨機 1500~2500W
        load_w = max(500.0, round(2000 + 500 * math.sin(t * 0.8) + 150 * math.cos(t * 2.1), 1))
        # 電池充放電 (瓦特): 太陽能多時充電 (負值為放電，正值為充電)
        battery_w = round((solar_w - load_w) * 0.7, 1)
        # 電網 (瓦特): 平衡剩餘功率 (負值為躉售/送回電網，正值為從電網買電)
        grid_w = round(load_w - (solar_w - battery_w), 1)
        # 電池電量百分比 (SoC): 介於 70% ~ 90%
        soc_pct = round(80.0 + 8.0 * math.sin(t * 0.05), 1)

        iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if parsed.path == '/api/meters/aggregates':
            # Tesla Powerwall 核心電表聚合端點 (即時功率)
            data = {
                "site": {
                    "instant_power": grid_w,
                    "instant_reactive_power": round(grid_w * 0.1, 1),
                    "instant_apparent_power": abs(grid_w),
                    "frequency": 60.0,
                    "energy_exported": 15420000,
                    "energy_imported": 23410000,
                    "instant_average_voltage": 220.4,
                    "last_communication_time": iso_time
                },
                "battery": {
                    "instant_power": battery_w,
                    "instant_reactive_power": 0.0,
                    "instant_apparent_power": abs(battery_w),
                    "frequency": 60.0,
                    "energy_exported": 8940000,
                    "energy_imported": 9120000,
                    "instant_average_voltage": 220.0,
                    "last_communication_time": iso_time
                },
                "load": {
                    "instant_power": load_w,
                    "instant_reactive_power": round(load_w * 0.05, 1),
                    "instant_apparent_power": load_w,
                    "frequency": 60.0,
                    "energy_exported": 0,
                    "energy_imported": 45120000,
                    "instant_average_voltage": 220.2,
                    "last_communication_time": iso_time
                },
                "solar": {
                    "instant_power": solar_w,
                    "instant_reactive_power": 0.0,
                    "instant_apparent_power": solar_w,
                    "frequency": 60.0,
                    "energy_exported": 58910000,
                    "energy_imported": 0,
                    "instant_average_voltage": 220.1,
                    "last_communication_time": iso_time
                }
            }
            self._send_json(data, 200)

        elif parsed.path == '/api/system_status/soe':
            # 電池可用電量 (State of Energy)
            data = {
                "percentage": soc_pct
            }
            self._send_json(data, 200)

        elif parsed.path == '/api/system_status/grid_status':
            # 電網連接狀態 (Connected / Islanded)
            data = {
                "grid_status": "SystemGridConnected",
                "grid_services_active": False
            }
            self._send_json(data, 200)

        elif parsed.path == '/api/sitemaster':
            data = {
                "status": "Up",
                "running": True,
                "connected_to_tesla": True,
                "powerwall_on": True,
                "powerwall_battery_online": True
            }
            self._send_json(data, 200)

        elif parsed.path == '/api/site_info':
            data = {
                "max_site_meter_power_ac": 10000,
                "min_site_meter_power_ac": -10000,
                "nominal_system_energy_kWh": 13.5,
                "site_name": "Demo Energy Site 1",
                "grid_code": "60Hz_220V"
            }
            self._send_json(data, 200)

        else:
            self._send_json({
                "status": "online",
                "message": "Mock Tesla Powerwall 2 Gateway is running",
                "supported_endpoints": [
                    "/api/login/Basic",
                    "/api/meters/aggregates",
                    "/api/system_status/soe",
                    "/api/system_status/grid_status",
                    "/api/sitemaster",
                    "/api/site_info"
                ]
            }, 200)

def run_server(port=PORT):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, MockTegHandler)
    print("=" * 60)
    print(f"[*] Mock Tesla Powerwall 2 Gateway (TEG) 已啟動")
    print(f"[*] 監聽位址: http://127.0.0.1:{port} (或本機區域網路 IP)")
    print(f"[*] 提供端點:")
    print(f"    - POST /api/login/Basic")
    print(f"    - GET  /api/meters/aggregates (動態功率波動)")
    print(f"    - GET  /api/system_status/soe (電池 SoC %)")
    print(f"    - GET  /api/system_status/grid_status")
    print(f"[*] 按 Ctrl+C 可停止伺服器")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] 正在關閉 Mock TEG 伺服器...")
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
