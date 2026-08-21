from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class DelegationSpec(BaseModel):
    delegation_id: str
    parent_agent_id: str
    child_agent_id: str
    max_sub_budget: float
    allowed_resources: List[str]

class ActionProposal(BaseModel):
    human_owner_id: str
    agent_id: str
    delegation_chain: List[DelegationSpec]
    target_resource: str
    proposed_action: str
    requested_amount: float

class AuthorizationResult(BaseModel):
    authorized: bool
    reason: str
    execution_token: Optional[str] = None
    remaining_delegated_budget: float

class ExecutionRequest(BaseModel):
    execution_token: str
    action_payload: Dict[str, Any]

class ExecutionEvidence(BaseModel):
    evidence_id: str
    delegation_root: str
    agent_id: str
    action: str
    status: str
    amount_spent: float
    proof_hash: str
    prev_proof_hash: str
