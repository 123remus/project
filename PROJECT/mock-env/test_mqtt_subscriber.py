"""
MQTT Telemetry Subscriber Test Tool
用來訂閱並即時顯示 Android 邊緣端發送的 MQTTS / MQTT 遙測訊息
主題格式: site/+/telemetry 與 site/+/status
"""

import json
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[!] 尚未安裝 paho-mqtt 套件。請先執行: pip install paho-mqtt")
    sys.exit(1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[+] 成功連線至 MQTT Broker!")
        # 訂閱所有案場的遙測數據與狀態
        client.subscribe("site/+/telemetry")
        client.subscribe("site/+/status")
        print("[*] 已訂閱主題: site/+/telemetry, site/+/status")
        print("=" * 80)
        print(f"{'主題':<24} | {'案場ID':<10} | {'太陽能(kW)':<10} | {'電網(kW)':<10} | {'電池(kW)':<10} | {'SoC(%)'}")
        print("-" * 80)
    else:
        print(f"[-] 連線失敗，代碼: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        topic = msg.topic
        
        if topic.endswith("/telemetry"):
            site_id = payload.get("site_id", "-")
            solar = payload.get("solar_kw", 0.0)
            grid = payload.get("grid_kw", 0.0)
            batt = payload.get("battery_kw", 0.0)
            soc = payload.get("soc_pct", 0.0)
            print(f"{topic:<24} | {site_id:<10} | {solar:<10.3f} | {grid:<10.3f} | {batt:<10.3f} | {soc:<5.1f}%")
        elif topic.endswith("/status"):
            print(f"[!] 案場狀態更新: {topic} -> {payload}")
    except Exception as e:
        print(f"[*] 收到原始訊息 [{msg.topic}]: {msg.payload.decode('utf-8', errors='ignore')}")

def main():
    broker_host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    broker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883

    print(f"[*] 正在連線至 MQTT Broker: {broker_host}:{broker_port}...")
    client = mqtt.Client(client_id="ems-test-subscriber")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker_host, broker_port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[*] 停止監聽。")
        client.disconnect()
    except Exception as e:
        print(f"[-] 連線發生錯誤: {e}")

if __name__ == '__main__':
    main()
