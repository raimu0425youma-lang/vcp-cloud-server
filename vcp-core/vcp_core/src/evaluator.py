import os
import re
import json
import hashlib
import openai
import anthropic
import google.generativeai as genai
from vcp_core.src.schema import AgentIdentity, PolicyRule, AIDecision, ExecutionEvidence

class VCPEvaluator:
    def __init__(self, identity: AgentIdentity, policy: PolicyRule):
        self.identity = identity
        self.policy = policy

    def evaluate(self, decision: AIDecision) -> ExecutionEvidence:
        provider = (decision.model_provider or "rule_engine").lower()
        keys = decision.user_api_keys or None

        intent = decision.user_intent.strip().lower()
        action = decision.proposed_action.lower()

        # 一次防御: ルールベース即時検知
        if len(intent) < 3 or intent.startswith("で") or intent in ["haj", "test", "aaa"]:
            return self._generate_evidence(decision, "遮断", f"入力不備: 目的（'{decision.user_intent}'）が解釈不能です。", provider)

        danger_keywords = ["無視", "bypass", "マイニング", "全削除", "権限奪取", "prompt injection"]
        for kw in danger_keywords:
            if kw in intent:
                return self._generate_evidence(decision, "遮断", f"セキュリティ違反: 危険指示キーワード（'{kw}'）を検出。", provider)

        # 二次防御: ユーザー持ち込みキー（BYOK）での実AI評価
        prompt = f"""
あなたはVCP Coreセキュリティゲートウェイです。以下のAIエージェントの申請を評価してください。
- 上限予算ポリシー: {self.policy.max_budget_jpy}円
- 許可アクション: {self.policy.allowed_actions}

【申請】
- 目的: {decision.user_intent}
- アクション: {decision.proposed_action}
- 見積コスト: {decision.estimated_cost_jpy}円

出力は必ず以下のJSON形式のみで回答してください:
{{"status": "許可" または "遮断", "reason": "判定理由の短い解説"}}
"""

        try:
            if provider == "openai":
                api_key = (keys.openai_key if keys else None) or os.getenv("OPENAI_API_KEY")
                if not api_key or len(api_key) < 15 or api_key.startswith("your_"):
                    return self._generate_evidence(decision, "遮断", "ユーザーAPIキー未設定: ChatGPTを使用するには「自分のAPIキー設定」からOpenAI Keyを入力してください。", "OpenAI (未設定)")
                client = openai.OpenAI(api_key=api_key)
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(res.choices[0].message.content)
                return self._generate_evidence(decision, data["status"], f"[ChatGPT-4o-mini] {data['reason']}", "ChatGPT")

            elif provider == "anthropic":
                api_key = (keys.anthropic_key if keys else None) or os.getenv("ANTHROPIC_API_KEY")
                if not api_key or len(api_key) < 15 or api_key.startswith("your_"):
                    return self._generate_evidence(decision, "遮断", "ユーザーAPIキー未設定: Claudeを使用するには「自分のAPIキー設定」からAnthropic Keyを入力してください。", "Claude (未設定)")
                client = anthropic.Anthropic(api_key=api_key)
                res = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = res.content[0].text
                data = json.loads(text[text.find("{"):text.rfind("}")+1])
                return self._generate_evidence(decision, data["status"], f"[Claude 3.5 Sonnet] {data['reason']}", "Claude")

            elif provider == "gemini":
                api_key = (keys.gemini_key if keys else None) or os.getenv("GEMINI_API_KEY")
                if not api_key or len(api_key) < 15 or api_key.startswith("your_"):
                    return self._generate_evidence(decision, "遮断", "ユーザーAPIキー未設定: Geminiを使用するには「自分のAPIキー設定」からGemini Keyを入力してください。", "Gemini (未設定)")
                
                genai.configure(api_key=api_key)
                
                # 有効なモデル候補リスト（自動試行順）
                candidate_models = [
                    "gemini-1.5-flash-latest",
                    "gemini-2.0-flash",
                    "gemini-1.5-flash-001",
                    "gemini-1.5-flash-002",
                    "gemini-1.5-pro",
                    "gemini-1.0-pro"
                ]

                # 現在のキーで利用可能なモデル一覧を取得して先頭に追加
                try:
                    live_models = []
                    for m in genai.list_models():
                        if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                            name_clean = m.name.replace('models/', '')
                            live_models.append(name_clean)
                    if live_models:
                        candidate_models = live_models + [m for m in candidate_models if m not in live_models]
                except Exception:
                    pass

                last_error = ""
                data = None
                used_model = None

                # 有効なモデルが見つかるまで順次実行
                for m_name in candidate_models:
                    try:
                        model = genai.GenerativeModel(m_name)
                        res = model.generate_content(prompt + "\nJSONのみで出力してください。")
                        text = res.text
                        start = text.find("{")
                        end = text.rfind("}") + 1
                        if start != -1 and end != 0:
                            data = json.loads(text[start:end])
                            used_model = m_name
                            break
                    except Exception as err:
                        last_error = str(err)
                        continue

                if not data:
                    return self._generate_evidence(decision, "遮断", f"Gemini API実行エラー: 有効なモデルの呼び出しに失敗しました ({last_error})", "Gemini")

                return self._generate_evidence(decision, data["status"], f"[{used_model}] {data['reason']}", "Gemini")

        except Exception as e:
            return self._generate_evidence(decision, "遮断", f"API実行エラー: {str(e)}", provider)

        # 標準フォールバック（内蔵ルールエンジン）
        match = re.search(r'(\d+)\s*万', intent)
        max_limit = float(match.group(1)) * 10000 if match else self.policy.max_budget_jpy
        
        if decision.estimated_cost_jpy > max_limit:
            return self._generate_evidence(decision, "遮断", f"[VCP Engine] 予算超過 ({decision.estimated_cost_jpy:,.0f}円 > 上限 {max_limit:,.0f}円)", "VCP Engine")
        
        if decision.proposed_action not in self.policy.allowed_actions:
            return self._generate_evidence(decision, "遮断", f"[VCP Engine] ポリシー違反: '{decision.proposed_action}' は未許可アクションです。", "VCP Engine")

        return self._generate_evidence(decision, "許可", f"[VCP Engine] 政策適合: 予算 ({decision.estimated_cost_jpy:,.0f}円) およびアクション整合性をクリア。", "VCP Engine")

    def _generate_evidence(self, decision: AIDecision, status: str, reason: str, provider: str) -> ExecutionEvidence:
        raw_data = f"{self.identity.agent_id}:{decision.proposed_action}:{status}:{reason}:{provider}"
        hash_val = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

        return ExecutionEvidence(
            agent_id=self.identity.agent_id,
            action_type=decision.proposed_action,
            status=status,
            reason=reason,
            evidence_hash=hash_val,
            provider_used=provider
        )
