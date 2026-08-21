import os
from vcp_sdk import vcp_guard, DelegationContext

# 古いログをリセット
if os.path.exists("vcp_evidence.jsonl"):
    os.remove("vcp_evidence.jsonl")

@vcp_guard(action="create_ec2", resource="aws_ec2", amount=40000)
def deploy_server():
    print("  └─ AI: サーバーを構築しています...")

print("=== [ステップ 1: 親(CEO) ➔ 子(Purchasing Agent) への権限委譲 (予算4万 / ポリシー内)] ===")
with DelegationContext(parent_id="agent_ceo", agent_id="agent_purchasing", delegated_budget=50000):
    try:
        deploy_server()
    except Exception as e:
        print(f"Error: {e}")

print("\n=== [ステップ 2: 委譲枠（2万円）を超えるアクションを発行した場合] ===")
with DelegationContext(parent_id="agent_ceo", agent_id="agent_purchasing", delegated_budget=20000):
    try:
        deploy_server()
    except Exception as e:
        pass

print("\n=== [生成された証跡チェーン (vcp_evidence.jsonl)] ===")
with open("vcp_evidence.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())
