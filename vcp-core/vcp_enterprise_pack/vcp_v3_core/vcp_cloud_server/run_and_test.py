import subprocess
import time
import requests
import sys

print("=== [ステップ 1: SaaSバックエンドサーバー起動] ===")
server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--port", "8000"])
time.sleep(2)  # 起動待ち

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "vcp_live_tier_enterprise_999"
HEADERS = {"X-API-Key": API_KEY}

try:
    print("\n=== [ステップ 2: リモートポリシー取得 (SDKと同期)] ===")
    res_policy = requests.get(f"{BASE_URL}/v1/policy/sync", headers=HEADERS)
    print(f"同期結果: {res_policy.json()}")

    print("\n=== [ステップ 3: ログ一元送信 ＆ 課金カウンター同期] ===")
    telemetry_data = {
        "events": [
            {
                "token_id": "tok_001",
                "action": "create_instance",
                "resource": "aws_ec2",
                "amount": 30000.0,
                "status": "EXECUTED",
                "proof_hash": "a1b2c3d4...",
                "timestamp": time.time()
            }
        ]
    }
    res_ingest = requests.post(f"{BASE_URL}/v1/telemetry/ingest", headers=HEADERS, json=telemetry_data)
    print(f"送信結果: {res_ingest.json()}")

    print("\n=== [ステップ 4: SaaSダッシュボード（課金状況確認）] ===")
    res_dash = requests.get(f"{BASE_URL}/v1/dashboard/usage", headers=HEADERS)
    print(f"ダッシュボード画面情報: {res_dash.json()}")

finally:
    print("\n=== [テスト完了: サーバー停止] ===")
    server_process.terminate()
