import functools
import yaml
import os
import json
import hashlib
import time
from contextvars import ContextVar

# スレッド/非同期セーフな委譲コンテキスト管理
_current_delegation = ContextVar("delegation", default=None)

class DelegationContext:
    def __init__(self, parent_id: str, agent_id: str, delegated_budget: float):
        self.parent_id = parent_id
        self.agent_id = agent_id
        self.delegated_budget = delegated_budget
        self._token = None

    def __enter__(self):
        self._token = _current_delegation.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _current_delegation.reset(self._token)

class VCPClient:
    _policy = None
    _last_hash = "0" * 64
    _log_file = "vcp_evidence.jsonl"

    @classmethod
    def load_policy(cls, filepath="policy.yaml"):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                cls._policy = yaml.safe_load(f)
        else:
            cls._policy = {}

    @classmethod
    def request_authorization(cls, action: str, resource: str, amount: float):
        if not cls._policy:
            cls.load_policy()

        context = _current_delegation.get()
        agent_info = f"Agent '{context.agent_id}' (Parent: {context.parent_id})" if context else "Unknown Agent"

        # リソース & アクション検証
        if cls._policy.get("target_resource") != resource:
            return False, f"[{agent_info}] 未許可リソース '{resource}'"
        if action not in cls._policy.get("allowed_actions", []):
            return False, f"[{agent_info}] 未許可アクション '{action}'"

        # 予算上限 ＆ 委譲枠検証
        max_policy_budget = cls._policy.get("max_budget_per_action", 0)
        allowed_budget = max_policy_budget
        if context:
            allowed_budget = min(allowed_budget, context.delegated_budget)

        if amount > allowed_budget:
            return False, f"[{agent_info}] 予算超過 (申請: {amount:,.0f}円 / 許容枠: {allowed_budget:,.0f}円)"

        return True, "【VCP 承認完了】"

    @classmethod
    def submit_evidence(cls, action: str, resource: str, amount: float, status: str):
        context = _current_delegation.get()
        agent_id = context.agent_id if context else "standalone"
        parent_id = context.parent_id if context else "none"

        prev_hash = cls._last_hash
        timestamp = time.time()
        raw_data = f"{prev_hash}:{parent_id}:{agent_id}:{action}:{amount}:{status}:{timestamp}"
        current_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()
        cls._last_hash = current_hash

        entry = {
            "timestamp": timestamp,
            "parent_id": parent_id,
            "agent_id": agent_id,
            "action": action,
            "resource": resource,
            "amount": amount,
            "status": status,
            "proof_hash": current_hash,
            "prev_proof_hash": prev_hash
        }

        with open(cls._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"  └─ 🛡️ [Evidence Locked] Hash: {current_hash[:16]}... (Prev: {prev_hash[:8]}...)")

def vcp_guard(action: str, resource: str, amount: float = 0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            authorized, reason = VCPClient.request_authorization(action, resource, amount)
            if not authorized:
                print(f"  └─ ⛔ [VCP BLOCK] {reason}")
                VCPClient.submit_evidence(action, resource, amount, "BLOCKED")
                raise PermissionError(reason)
            
            result = func(*args, **kwargs)
            VCPClient.submit_evidence(action, resource, amount, "EXECUTED")
            return result
        return wrapper
    return decorator
