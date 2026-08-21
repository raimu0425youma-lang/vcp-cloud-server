import functools
import yaml
import os
import json
import hashlib
import time
from contextvars import ContextVar

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

class VCPSDKEngine:
    def __init__(self, policy_path="policy.yaml"):
        self.policy_path = policy_path
        self._policy = {}
        self._last_hash = "0" * 64
        self.load_policy()

    def load_policy(self):
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r", encoding="utf-8") as f:
                self._policy = yaml.safe_load(f)

    def authorize(self, action: str, resource: str, amount: float):
        context = _current_delegation.get()
        agent_info = f"Agent '{context.agent_id}'" if context else "Standalone Agent"

        if self._policy.get("target_resource") != resource:
            return False, f"[{agent_info}] 未許可リソース '{resource}'"

        max_budget = self._policy.get("max_budget_per_action", 0)
        if context:
            max_budget = min(max_budget, context.delegated_budget)

        if amount > max_budget:
            return False, f"[{agent_info}] 許容上限 ({max_budget:,.0f}円) 超過"

        return True, "承認"

    def record_evidence(self, action: str, resource: str, amount: float, status: str):
        context = _current_delegation.get()
        prev_hash = self._last_hash
        timestamp = time.time()
        
        raw_data = f"{prev_hash}:{action}:{amount}:{status}:{timestamp}"
        current_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()
        self._last_hash = current_hash

        entry = {
            "timestamp": timestamp,
            "agent_id": context.agent_id if context else "anon",
            "action": action,
            "resource": resource,
            "amount": amount,
            "status": status,
            "proof_hash": current_hash,
            "prev_hash": prev_hash
        }

        with open("vcp_evidence.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        return entry
