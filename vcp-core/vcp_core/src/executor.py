import json
import os
from vcp_core.src.schema import AIDecision, ExecutionEvidence

class VCPExecutor:
    def __init__(self, log_path: str = "vcp_core/logs/evidence.jsonl"):
        self.log_path = log_path

    def execute_and_log(self, decision: AIDecision, evidence: ExecutionEvidence) -> dict:
        result = {
            "evidence": evidence.dict(),
            "action_executed": False,
            "action_output": None
        }

        # ALLOWEDのときだけActionを実行（Mock）
        if evidence.status == "ALLOWED":
            output = self._mock_action_execution(decision)
            result["action_executed"] = True
            result["action_output"] = output

        # Evidence（検証証拠）を永続化ログファイルに書き込み
        self._save_log(result)
        return result

    def _mock_action_execution(self, decision: AIDecision) -> dict:
        if decision.proposed_action == "create_ec2":
            return {
                "status": "SUCCESS",
                "resource_id": "i-0abc12345def6789a",
                "message": f"Mock EC2 instance ({decision.parameters.get('instance_type', 't3.micro')}) created."
            }
        return {"status": "SUCCESS", "message": f"Mock action '{decision.proposed_action}' completed."}

    def _save_log(self, data: dict):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
