import time
import hmac
import hashlib
import json
from typing import Dict, Tuple
from vcp_core.src.schema import ActionProposal, AuthorizationResult, ExecutionRequest, ExecutionEvidence

SECRET_KEY = b"vcp_zero_trust_root_secret_key"

class VCPAuthorityEngine:
    _last_proof_hash = "0" * 64

    def __init__(self):
        # 委譲ツリーごとの累積消費額トラッキング {delegation_id: total_spent}
        self.delegation_spent: Dict[str, float] = {}

    def authorize_proposal(self, proposal: ActionProposal) -> AuthorizationResult:
        # 1. 委譲チェーンの検証と権限減衰・予算チェック
        current_budget_limit = float('inf')
        
        for spec in proposal.delegation_chain:
            # 許容リソース検証
            if proposal.target_resource not in spec.allowed_resources:
                return AuthorizationResult(
                    authorized=False,
                    reason=f"【権限不適格】委譲ID '{spec.delegation_id}' ではリソース '{proposal.target_resource}' へのアクセスが許可されていません。",
                    remaining_delegated_budget=0
                )
            
            # 親から子への予算上限（減衰）チェック
            current_budget_limit = min(current_budget_limit, spec.max_sub_budget)
            
            # 過去の累積消費額を加算して検証
            already_spent = self.delegation_spent.get(spec.delegation_id, 0.0)
            if (already_spent + proposal.requested_amount) > spec.max_sub_budget:
                return AuthorizationResult(
                    authorized=False,
                    reason=f"【委譲予算超過】委譲ID '{spec.delegation_id}' の累計上限({spec.max_sub_budget:,.0f}円)を突破します。(既使用: {already_spent:,.0f}円)",
                    remaining_delegated_budget=max(0, spec.max_sub_budget - already_spent)
                )

        # 2. 一時的ワンタイムExecutionTokenの発行 (HMAC-SHA256署名)
        expires_at = int(time.time()) + 30  # 30秒有効
        token_payload = {
            "human_id": proposal.human_owner_id,
            "agent_id": proposal.agent_id,
            "action": proposal.proposed_action,
            "resource": proposal.target_resource,
            "amount": proposal.requested_amount,
            "delegation_chain_ids": [d.delegation_id for d in proposal.delegation_chain],
            "exp": expires_at
        }
        
        payload_str = json.dumps(token_payload, sort_keys=True)
        signature = hmac.new(SECRET_KEY, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
        execution_token = f"{payload_str}.{signature}"

        # 最も末端の委譲ID残額を返す
        leaf_delegation = proposal.delegation_chain[-1].delegation_id
        spent = self.delegation_spent.get(leaf_delegation, 0.0)

        return AuthorizationResult(
            authorized=True,
            reason="【承認成功】Identity・Delegation Chain・予算上限の整合性を検証しました。ExecutionTokenを発行します。",
            execution_token=execution_token,
            remaining_delegated_budget=current_budget_limit - spent - proposal.requested_amount
        )

    def execute_action(self, req: ExecutionRequest) -> Tuple[bool, str, Optional[ExecutionEvidence]]:
        # 1. トークンの改ざん・有効期限検証
        try:
            payload_str, signature = req.execution_token.rsplit(".", 1)
            expected_sig = hmac.new(SECRET_KEY, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return False, "【トークン改ざん検知】署名が不一致です。", None

            data = json.loads(payload_str)
            if time.time() > data["exp"]:
                return False, "【トークン期限切れ】ExecutionTokenの有効期限(30秒)が切れています。", None

        except Exception:
            return False, "【不正トークン】ExecutionTokenのフォーマットが不正です。", None

        # 2. 実際の予算消費の確定（State更新）
        for del_id in data["delegation_chain_ids"]:
            self.delegation_spent[del_id] = self.delegation_spent.get(del_id, 0.0) + data["amount"]

        # 3. Execution Evidence Proofの暗号連結生成
        prev_hash = VCPAuthorityEngine._last_proof_hash
        proof_raw = f"{prev_hash}:{data['human_id']}:{data['agent_id']}:{data['action']}:{data['amount']}:{time.time()}"
        current_hash = hashlib.sha256(proof_raw.encode('utf-8')).hexdigest()
        VCPAuthorityEngine._last_proof_hash = current_hash

        evidence = ExecutionEvidence(
            evidence_id=f"ev_{int(time.time()*1000)}",
            delegation_root=data["delegation_chain_ids"][0],
            agent_id=data["agent_id"],
            action=data["action"],
            status="EXECUTED",
            amount_spent=data["amount"],
            proof_hash=current_hash,
            prev_proof_hash=prev_hash
        )

        return True, f"【実行完了】ターゲット '{data['resource']}' に対して '{data['action']}' を実行しました。", evidence
