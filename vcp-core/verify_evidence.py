import json
import hashlib
import sys

def verify_chain(filepath="vcp_evidence.jsonl"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print("❌ ログファイルが存在しません。")
        return False

    if not lines:
        print("❌ ログファイルが空です。")
        return False

    prev_hash = "0" * 64
    count = 0

    for line_num, line in enumerate(lines, 1):
        entry = json.loads(line)
        
        # 1. 前回ハッシュとの接合チェック
        if entry["prev_proof_hash"] != prev_hash:
            print(f"⛔ 【改ざん検知】 Line {line_num}: ハッシュチェーンの不整合を検出しました。")
            print(f"   期待された前ハッシュ: {prev_hash[:16]}...")
            print(f"   記録されている前ハッシュ: {entry['prev_proof_hash'][:16]}...")
            return False

        # 2. ログデータのハッシュ再計算と照合
        raw_data = f"{entry['prev_proof_hash']}:{entry['parent_id']}:{entry['agent_id']}:{entry['action']}:{entry['amount']}:{entry['status']}:{entry['timestamp']}"
        expected_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

        if entry["proof_hash"] != expected_hash:
            print(f"⛔ 【改ざん検知】 Line {line_num}: ログ内データの改ざんを検出しました！")
            print(f"   本来の算出ハッシュ: {expected_hash[:16]}...")
            print(f"   改ざん済みログハッシュ: {entry['proof_hash'][:16]}...")
            return False

        prev_hash = entry["proof_hash"]
        count += 1

    print(f"✅ 【検証成功】 全 {count} 件の Evidence ログは改ざんされておらず、暗号的に正当性が証明されました。")
    return True

if __name__ == "__main__":
    verify_chain()
