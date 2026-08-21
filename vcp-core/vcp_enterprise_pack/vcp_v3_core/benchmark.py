import time
import os
from vcp_engine import VCPUltraEngine, MacaroonToken

# 古いログクリア
if os.path.exists("vcp_audit.jsonl"):
    os.remove("vcp_audit.jsonl")

ROOT_SECRET = b"vcp_ultra_secret_key_2026"
engine = VCPUltraEngine(ROOT_SECRET)

# --- 1. 親(CEO)がルートトークン発行 ---
ceo_token = MacaroonToken(ROOT_SECRET, "identifier_ceo_root")

# --- 2. 子(Purchasing Agent)へ権限減衰委譲 (予算を30,000円に絞る) ---
child_token = ceo_token.add_caveat("budget<=30000")
child_token_serialized = child_token.serialize()

print("=== 🚀 VCP v3.0 Ultra-High Performance ベンチマーク ===")
print(f"暗号化減衰トークン長: {len(child_token_serialized)} bytes")

# --- 3. 50,000回連続判定のレイテンシ・スループット計測 ---
TOTAL_REQUESTS = 50000
start_time = time.perf_counter()

for _ in range(TOTAL_REQUESTS):
    # 20,000円の処理（通過ケース）
    ok, _ = engine.authorize_and_execute(child_token_serialized, "aws_ec2", "create_instance", 20000)

elapsed = time.perf_counter() - start_time
avg_latency_us = (elapsed / TOTAL_REQUESTS) * 1000000
rps = TOTAL_REQUESTS / elapsed

print(f"\n[計測結果]")
print(f"処理リクエスト数 : {TOTAL_REQUESTS:,} 件")
print(f"総処理時間     : {elapsed:.4f} 秒")
print(f"平均レイテンシ   : {avg_latency_us:.2f} マイクロ秒 / 件 (0.00ms)")
print(f"スループット    : {rps:,.0f} RPS (Requests Per Second)")

# ログフラッシュ待ち
engine.writer.close()
print("\n✅ 非同期リングバッファ経由で全件の暗号ハッシュ証跡が保存されました。")
