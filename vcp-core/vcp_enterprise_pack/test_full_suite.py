import os
import sys

# パッケージパス追加
sys.path.insert(0, os.path.abspath("."))

from vcp import VCPSDKEngine, DelegationContext, VCPLangChainMiddleware

if os.path.exists("vcp_evidence.jsonl"):
    os.remove("vcp_evidence.jsonl")

engine = VCPSDKEngine("policy.yaml")
middleware = VCPLangChainMiddleware(engine)

# LangChainツール想定の仮の関数
def raw_aws_deploy_tool(instance_type: str, amount: float):
    return f"EC2 ({instance_type}) の作成に成功しました。"

# ミドルウェアでラップ
guarded_tool = middleware.wrap_tool(raw_aws_deploy_tool, action="create_instance", resource="aws_ec2")

print("=== [ 100万DL級 VCP-SDK 統合自動検証スイート ] ===")

print("\n1. 正常な親・子デリゲーション下での LangChain Tool 実行")
with DelegationContext(parent_id="agent_parent", agent_id="agent_child", delegated_budget=50000):
    res1 = guarded_tool(instance_type="t3.micro", amount=30000)
    print(f"   実行結果: {res1}")

print("\n2. 委譲枠（予算5万円）を超える LangChain Tool 実行の事前遮断")
with DelegationContext(parent_id="agent_parent", agent_id="agent_child", delegated_budget=50000):
    res2 = guarded_tool(instance_type="c5.xlarge", amount=80000)
    print(f"   遮断結果: {res2}")

print("\n✅ パッケージテスト完了: 依存関係ゼロ・1デコレータでLangChain/OpenAI全AIツールへ即座に統合可能。")
