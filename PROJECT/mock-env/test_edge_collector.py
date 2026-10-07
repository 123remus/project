"""
Test Edge Collector Script (獨立測試腳本)
模擬 Android 端點上的 Chaquopy Python Runtime 執行的核心採集邏輯。
可對接實體 TEG 或 Mock TEG 伺服器，驗證數據獲取與格式化是否符合標準 EMS 規範。
"""

import json
import ssl
import sys
import time
import urllib.request
import urllib.error

class PowerwallCollector:
    def __init__(self, host="127.0.0.1:8675", password="mock_password", email="customer@example.com", use_ssl=False):
        self.host = host.rstrip('/')
        self.password = password
        self.email = email
        self.use_ssl = use_ssl
        self.scheme = "https" if use_ssl else "http"
        self.token = None
        self.cookie = None
        
        # 建立略過自簽名憑證檢查的 SSL Context (相容實體 TEG self-signed cert)
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def login(self):
        """向 TEG 發起登入以取得認證 Cookie / Token"""
        url = f"{self.scheme}://{self.host}/api/login/Basic"
        payload = json.dumps({
            "username": "customer",
            "password": self.password,
            "email": self.email,
            "force_sm_off": False
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, context=self.ctx if self.use_ssl else None, timeout=5) as resp:
                headers = resp.info()
                self.cookie = headers.get('Set-Cookie')
                body = resp.read().decode('utf-8')
                data = json.loads(body)
                self.token = data.get("token")
                return True, "Login successful"
        except urllib.error.HTTPError as e:
            # 部分舊款 TEG 可能不需要或不同登入路徑
            return False, f"HTTP Error {e.code}: {e.reason}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def _http_get(self, path):
        """發送 GET 請求並帶上認證 Cookie"""
        url = f"{self.scheme}://{self.host}{path}"
        headers = {'User-Agent': 'EMS-Edge-Android-Chaquopy/1.0'}
        if self.cookie:
            headers['Cookie'] = self.cookie
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=self.ctx if self.use_ssl else None, timeout=4) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def poll_telemetry(self, site_id="site_01"):
        """採集即時聚合功率與電池電量，封裝為標準遙測 JSON"""
        try:
            # 1. 讀取電表功率聚合 (/api/meters/aggregates)
            aggregates = self._http_get("/api/meters/aggregates")
            
            # 2. 讀取電池可用電量 (/api/system_status/soe)
            soe_data = self._http_get("/api/system_status/soe")

            # 3. 讀取電網狀態 (可選)
            grid_status = "Connected"
            try:
                grid_info = self._http_get("/api/system_status/grid_status")
                grid_status = grid_info.get("grid_status", "Connected")
                if "GridConnected" in grid_status:
                    grid_status = "Connected"
                elif "Islanded" in grid_status:
                    grid_status = "Islanded"
            except Exception:
                pass

            # 提取功率數據 (轉為 kW，取兩位小數)
            solar_kw = round(aggregates.get("solar", {}).get("instant_power", 0.0) / 1000.0, 3)
            grid_kw = round(aggregates.get("site", {}).get("instant_power", 0.0) / 1000.0, 3)
            battery_kw = round(aggregates.get("battery", {}).get("instant_power", 0.0) / 1000.0, 3)
            home_kw = round(aggregates.get("load", {}).get("instant_power", 0.0) / 1000.0, 3)
            soc_pct = round(soe_data.get("percentage", 0.0), 1)

            telemetry = {
                "site_id": site_id,
                "timestamp": int(time.time()),
                "solar_kw": solar_kw,
                "grid_kw": grid_kw,
                "battery_kw": battery_kw,
                "home_kw": home_kw,
                "soc_pct": soc_pct,
                "grid_status": grid_status,
                "status": "online"
            }
            return True, telemetry

        except Exception as e:
            # 失敗時嘗試重新登入
            self.login()
            return False, {"error": str(e), "timestamp": int(time.time())}

def main():
    target_host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8675"
    use_ssl = target_host.endswith(":443") or target_host.endswith(":8443")
    
    print(f"[*] 正在連線至 TEG 閘道器: {target_host} (SSL: {use_ssl})")
    collector = PowerwallCollector(host=target_host, use_ssl=use_ssl)
    
    ok, msg = collector.login()
    print(f"[*] 登入嘗試結果: {ok} ({msg})")

    print("[*] 開始輪詢遙測數據 (每 2 秒一次，按 Ctrl+C 中斷)...")
    print(f"{'時間戳':<12} | {'太陽能(kW)':<10} | {'電網(kW)':<10} | {'電池(kW)':<10} | {'家庭用電(kW)':<12} | {'SoC(%)':<8} | {'電網狀態'}")
    print("-" * 85)

    try:
        while True:
            success, data = collector.poll_telemetry(site_id="site_01")
            if success:
                print(f"{data['timestamp']:<12} | "
                      f"{data['solar_kw']:<10.3f} | "
                      f"{data['grid_kw']:<10.3f} | "
                      f"{data['battery_kw']:<10.3f} | "
                      f"{data['home_kw']:<12.3f} | "
                      f"{data['soc_pct']:<8.1f} | "
                      f"{data['grid_status']}")
            else:
                print(f"[!] 採集失敗: {data.get('error')}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[*] 測試停止。")

if __name__ == '__main__':
    main()
