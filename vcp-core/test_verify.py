import json
from verify_evidence import verify_chain

print("=== [ステップ 1: 正常な Evidence ログの暗号検証] ===")
if not verify_chain():
    exit()

print("\n=== [ステップ 2: 攻撃者がログ（40,000円 ➔ 1,000円）へ改ざんを試みた場合] ===")

# ログファイルを読み込んで、金額データを1,000円に悪意を持って書き換え
with open("vcp_evidence.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()

if lines:
    tampered_entry = json.loads(lines[0])
    tampered_entry["amount"] = 1000.0  # 改ざん実行
    lines[0] = json.dumps(tampered_entry, ensure_ascii=False) + "\n"

    with open("vcp_evidence.jsonl", "w", encoding="utf-8") as f:
        f.writelines(lines)

print("└─ 攻撃者: ログ内の消費金額を 40,000円 から 1,000円 に改ざんしました。")

print("\n=== [ステップ 3: 改ざん後の検証実行] ===")
verify_chain()
