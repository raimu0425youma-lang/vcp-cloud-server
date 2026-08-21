import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from vcp_core.src.schema import AgentIdentity, PolicyRule, AIDecision
from vcp_core.src.evaluator import VCPEvaluator
from vcp_core.src.executor import VCPExecutor

identity = AgentIdentity(agent_id="agent-001", owner_id="user-raimu")
policy = PolicyRule(max_budget_jpy=100000.0, allowed_actions=["create_ec2"])

evaluator = VCPEvaluator(identity=identity, policy=policy)
executor = VCPExecutor()

print("=== VCP Core エンドツーエンド実行パイプライン ===\n")

# テスト1: 許可ケース（Action実行まで進む）
d1 = AIDecision(
    user_intent="10万円以内でサーバー構築",
    proposed_action="create_ec2",
    estimated_cost_jpy=30000.0,
    parameters={"instance_type": "t3.medium"}
)
e1 = evaluator.evaluate(d1)
res1 = executor.execute_and_log(d1, e1)
print(f"[1. 許可ケース] 判定: {e1.status}")
print(f"    Action実行有無: {res1['action_executed']}")
print(f"    Action出力: {res1['action_output']}\n")

# テスト2: 遮断ケース（Actionは実行されない）
d2 = AIDecision(
    user_intent="データベース削除",
    proposed_action="delete_database",
    estimated_cost_jpy=0.0
)
e2 = evaluator.evaluate(d2)
res2 = executor.execute_and_log(d2, e2)
print(f"[2. 遮断ケース] 判定: {e2.status}")
print(f"    Action実行有無: {res2['action_executed']}")
print(f"    Action出力: {res2['action_output']}\n")
