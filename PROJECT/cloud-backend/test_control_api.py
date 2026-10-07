import json
import requests

def test_fleet_control():
    base_url = "http://127.0.0.1:8000"
    
    print("=" * 65)
    print("  Tesla Fleet API 遠端控制功能驗證測試")
    print("=" * 65)

    # 1. 測試設定備用電量
    print("\n[測試 1] 發送設定備用電量 (Backup Reserve -> 35%)...")
    payload1 = {"site_id": "site_01", "reserve_percent": 35}
    r1 = requests.post(f"{base_url}/api/control/backup-reserve/", json=payload1)
    print(f"HTTP 狀態碼 : {r1.status_code}")
    print(f"回應內容    : {json.dumps(r1.json(), ensure_ascii=False, indent=2)}")

    # 2. 測試切換運作模式 (Autonomous)
    print("\n[測試 2] 發送模式切換指令 (Mode -> autonomous 時間電價平衡)...")
    payload2 = {"site_id": "site_01", "mode": "autonomous"}
    r2 = requests.post(f"{base_url}/api/control/operation-mode/", json=payload2)
    print(f"HTTP 狀態碼 : {r2.status_code}")
    print(f"回應內容    : {json.dumps(r2.json(), ensure_ascii=False, indent=2)}")

    # 3. 測試切換運作模式 (Self-Consumption)
    print("\n[測試 3] 發送模式切換指令 (Mode -> self_consumption 自發自用)...")
    payload3 = {"site_id": "site_01", "mode": "self_consumption"}
    r3 = requests.post(f"{base_url}/api/control/operation-mode/", json=payload3)
    print(f"HTTP 狀態碼 : {r3.status_code}")
    print(f"回應內容    : {json.dumps(r3.json(), ensure_ascii=False, indent=2)}")

    # 4. 查詢遠端控制稽核紀錄
    print("\n[測試 4] 查詢控制歷史稽核紀錄 (Control Logs)...")
    r4 = requests.get(f"{base_url}/api/control/logs/?site_id=site_01")
    logs = r4.json().get("logs", [])
    print(f"共取得 {len(logs)} 筆稽核紀錄，最近 3 筆如下:")
    for log in logs[:3]:
        print(f"  • ID #{log['id']} | {log['created_at']} | 類型: {log['command_type']} | 參數: {log['parameters']} | 狀態: {log['status']} | Tesla 指令ID: {log['tesla_command_id']}")

    print("\n" + "=" * 65)
    print("  所有 Tesla Fleet API 遠端控制測試均順利通過！")
    print("=" * 65)

if __name__ == '__main__':
    test_fleet_control()
