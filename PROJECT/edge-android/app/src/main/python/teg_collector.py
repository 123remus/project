"""
TEG Collector for Chaquopy Runtime
在 Android 邊緣端運行的 Python 模組，專責與 Tesla Powerwall 2 Gateway (TEG) 本地通訊。
支援 pypowerwall 官方/社群標準連線，並內建高效能 Token 快取與自簽憑證寬容機制。
"""

import json
import ssl
import time
import urllib.request
import urllib.error

# 全域快取狀態（避免每次輪詢都重新向 TEG 登入）
_CACHED_SESSION = {
    "host": None,
    "cookie": None,
    "token": None,
    "last_login_time": 0
}

def _get_ssl_context():
    """建立略過本機自簽憑證檢查的 SSL Context (相容 TEG 自簽名憑證)"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def _login(host, password, email, use_ssl):
    """向 TEG 發起登入認證"""
    global _CACHED_SESSION
    scheme = "https" if use_ssl else "http"
    url = f"{scheme}://{host}/api/login/Basic"
    
    payload = json.dumps({
        "username": "customer",
        "password": password,
        "email": email,
        "force_sm_off": False
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Chaquopy-EMS/1.0'}
    )

    try:
        ctx = _get_ssl_context() if use_ssl else None
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            headers = resp.info()
            cookie = headers.get('Set-Cookie')
            body = resp.read().decode('utf-8')
            data = json.loads(body) if body else {}
            token = data.get("token")
            
            _CACHED_SESSION["host"] = host
            _CACHED_SESSION["cookie"] = cookie
            _CACHED_SESSION["token"] = token
            _CACHED_SESSION["last_login_time"] = time.time()
            return True, "Login OK"
    except Exception as e:
        return False, f"Login failed: {str(e)}"

def _http_get(host, path, use_ssl):
    """發送帶認證的 HTTP/HTTPS GET 請求"""
    global _CACHED_SESSION
    scheme = "https" if use_ssl else "http"
    url = f"{scheme}://{host}{path}"
    
    headers = {'User-Agent': 'Chaquopy-EMS/1.0'}
    if _CACHED_SESSION.get("cookie"):
        headers['Cookie'] = _CACHED_SESSION["cookie"]
    if _CACHED_SESSION.get("token"):
        headers['Authorization'] = f"Bearer {_CACHED_SESSION['token']}"

    req = urllib.request.Request(url, headers=headers)
    ctx = _get_ssl_context() if use_ssl else None
    with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
        return json.loads(resp.read().decode('utf-8'))

def collect_telemetry(host, password, email, site_id="site_01", use_ssl=False):
    """
    主要公開入口函數：供 Kotlin TegForegroundService 呼叫
    返回 JSON 字串，包含標準化遙測資料
    """
    global _CACHED_SESSION
    now = time.time()
    clean_host = host.replace("http://", "").replace("https://", "").rstrip('/')

    # 若尚未登入或主機更換、或 Token 已過期 15 分鐘，重新執行登入
    if (_CACHED_SESSION["host"] != clean_host or 
        not _CACHED_SESSION["token"] or 
        (now - _CACHED_SESSION["last_login_time"] > 900)):
        _login(clean_host, password, email, use_ssl)

    try:
        # 1. 讀取 /api/meters/aggregates
        aggregates = _http_get(clean_host, "/api/meters/aggregates", use_ssl)
        
        # 2. 讀取 /api/system_status/soe
        soe_data = _http_get(clean_host, "/api/system_status/soe", use_ssl)

        # 3. 讀取電網狀態
        grid_status = "Connected"
        try:
            grid_info = _http_get(clean_host, "/api/system_status/grid_status", use_ssl)
            raw_status = grid_info.get("grid_status", "Connected")
            grid_status = "Connected" if "Connected" in raw_status else "Islanded"
        except Exception:
            pass

        # 數值轉換：瓦特 (W) 轉千瓦 (kW)
        solar_w = aggregates.get("solar", {}).get("instant_power", 0.0)
        grid_w = aggregates.get("site", {}).get("instant_power", 0.0)
        battery_w = aggregates.get("battery", {}).get("instant_power", 0.0)
        home_w = aggregates.get("load", {}).get("instant_power", 0.0)
        soc_pct = soe_data.get("percentage", 0.0)

        result = {
            "site_id": site_id,
            "timestamp": int(now),
            "solar_kw": round(solar_w / 1000.0, 3),
            "grid_kw": round(grid_w / 1000.0, 3),
            "battery_kw": round(battery_w / 1000.0, 3),
            "home_kw": round(home_w / 1000.0, 3),
            "soc_pct": round(soc_pct, 1),
            "grid_status": grid_status,
            "is_success": True,
            "error_msg": ""
        }
        return json.dumps(result)

    except Exception as e:
        # 失敗時嘗試重新標記登入無效，下回重試
        _CACHED_SESSION["token"] = None
        error_result = {
            "site_id": site_id,
            "timestamp": int(now),
            "solar_kw": 0.0,
            "grid_kw": 0.0,
            "battery_kw": 0.0,
            "home_kw": 0.0,
            "soc_pct": 0.0,
            "grid_status": "Unknown",
            "is_success": False,
            "error_msg": str(e)
        }
        return json.dumps(error_result)
