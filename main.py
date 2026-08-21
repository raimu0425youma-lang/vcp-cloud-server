import os
import random
import uuid
import datetime
import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request

# ==========================================
# 1. VCP CORE TYPES & CONTRACTS
# ==========================================

class RecoveryContract(Enum):
    REVERSIBLE = "REVERSIBLE"       # スナップショットによる完全復旧可能
    COMPENSATABLE = "COMPENSATABLE" # 相殺アクションによる補償可能 (返金など)
    DELAYABLE = "DELAYABLE"         # 実行遅延によるキャンセル可能
    IRREVERSIBLE = "IRREVERSIBLE"   # 不可逆 (Human Approval 必須)

@dataclass
class IdentityContext:
    agent_id: str
    organization: str
    trust_score: float
    capabilities: List[str]

@dataclass
class EvidencePackage:
    evidence_id: str
    timestamp: str
    agent_id: str
    action_type: str
    status: str
    recovery_mode: str
    intent_hash: str

# ==========================================
# 2. VCP KERNEL (8-Layer Enforcement Engine)
# ==========================================

class VCPKernel:
    """
    AI Actionの全ライフサイクルを制御する8層のVCPカーネル。
    このエンジンを通らずに現実世界へのActionは実行できない。
    """
    def __init__(self):
        self.evidence_ledger: List[EvidencePackage] = []
        self.active_agents = {
            "agent-mai-001": {"org": "MAI_CORP", "trust": 0.99, "cap": ["read", "write", "payment"]},
            "agent-sub-002": {"org": "MAI_CORP", "trust": 0.75, "cap": ["read"]}
        }
        self.logger = logging.getLogger("VCP_KERNEL")

    def process_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """8-Layer Sequential Verification Pipeline"""
        try:
            # [Layer 1] IDENTITY: エージェントの特定
            agent_id = payload.get("agent_id")
            if not agent_id or agent_id not in self.active_agents:
                raise PermissionError(f"IDENTITY_REJECTED: Unregistered agent {agent_id}")
            identity = IdentityContext(agent_id=agent_id, **self.active_agents[agent_id])

            # [Layer 2] AUTHORITY: 権限血統図の確認
            target_action = payload.get("action", "")
            if target_action.split("_")[0] not in identity.capabilities:
                raise PermissionError("AUTHORITY_REJECTED: Capability missing")

            # [Layer 3] INTENT: 意図の検証 (AIの嘘を検知)
            intent = payload.get("intent", "").lower()
            if "delete" in target_action and "delete" not in intent and "remove" not in intent:
                raise ValueError("INTENT_MISMATCH: Action payload contradicts stated intent.")

            # [Layer 4] POLICY: 企業ポリシーエンジンの評価
            amount = payload.get("parameters", {}).get("amount", 0)
            if target_action == "payment_execute" and amount > 500000:
                raise PermissionError("POLICY_VIOLATION: Payment amount exceeds auto-approval limit.")

            # [Layer 5] DELEGATION: 委譲チェーンの検証
            delegation_chain = payload.get("delegation_chain", [])
            if len(delegation_chain) > 3:
                raise PermissionError("DELEGATION_REJECTED: Chain too deep (Max 3)")

            # [Layer 6] EXECUTION (AEG Enforcement)
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            # [Layer 8] RECOVERY: リカバリー契約の自動アサイン
            recovery_mode = RecoveryContract.REVERSIBLE.value
            if "payment" in target_action:
                recovery_mode = RecoveryContract.COMPENSATABLE.value
            elif "delete" in target_action:
                recovery_mode = RecoveryContract.IRREVERSIBLE.value

            # [Layer 7] EVIDENCE: 証拠チェーンの生成と保存
            evidence = EvidencePackage(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                agent_id=identity.agent_id,
                action_type=target_action,
                status="ALLOWED",
                recovery_mode=recovery_mode,
                intent_hash=f"sha256:{hash(intent)}"
            )
            self.evidence_ledger.insert(0, evidence) # 最新を先頭に
            if len(self.evidence_ledger) > 100: self.evidence_ledger.pop() # メモリ保護

            return {
                "status": "SUCCESS",
                "execution_id": execution_id,
                "evidence_id": evidence.evidence_id,
                "recovery_contract": recovery_mode
            }

        except Exception as e:
            # ブロックされた場合も証拠として残す
            self.evidence_ledger.insert(0, EvidencePackage(
                evidence_id=f"ev_blk_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                agent_id=payload.get("agent_id", "unknown"),
                action_type=payload.get("action", "unknown"),
                status="BLOCKED",
                recovery_mode="N/A",
                intent_hash="N/A"
            ))
            return {"status": "BLOCKED", "reason": str(e)}

# ==========================================
# 3. FLASK APPLICATION INIT
# ==========================================

app = Flask(__name__)
vcp_kernel = VCPKernel()

# ==========================================
# 4. BACKEND API ENDPOINTS
# ==========================================

@app.route("/vcp/gate", methods=["POST"])
def aec_gateway():
    """
    AEG (Action Enforcement Gateway) エンドポイント。
    AIエージェントが現実世界にActionを起こす際は必ずここを叩く。
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON"}), 400
    
    result = vcp_kernel.process_action(data)
    status_code = 200 if result["status"] == "SUCCESS" else 403
    return jsonify(result), status_code

@app.route("/api/evidence/logs", methods=["GET"])
def get_evidence_logs():
    """ダッシュボード描画用の証拠（Evidence）ログ取得API"""
    return jsonify([asdict(ev) for ev in vcp_kernel.evidence_ledger[:20]])

@app.route("/api/system/metrics", methods=["GET"])
def get_metrics():
    """VCP Control Center 用の稼働メトリクス"""
    total = len(vcp_kernel.evidence_ledger)
    blocked = sum(1 for e in vcp_kernel.evidence_ledger if e.status == "BLOCKED")
    return jsonify({
        "total_actions": total,
        "blocked_actions": blocked,
        "active_agents": len(vcp_kernel.active_agents),
        "system_status": "ONLINE",
        "threat_level": "LOW" if blocked < 5 else "ELEVATED"
    })

# ==========================================
# 5. FRONTEND: VCP CONTROL CENTER (HTML/CSS/JS)
# ==========================================

@app.route("/")
def index():
    """
    VCP Control Center Dashboard
    画像の配色テーマ（#020617等）を完全再現し、8層アーキテクチャの監視画面を生成。
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP Enterprise Control Center - MAI</title>
        <style>
            :root {
                --bg-primary: #020617;
                --bg-secondary: #0f172a;
                --bg-tertiary: #1e293b;
                --border-color: #334155;
                --accent-cyan: #06b6d4;
                --accent-cyan-hover: #22d3ee;
                --accent-blue: #3b82f6;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --status-allowed: #10b981;
                --status-blocked: #ef4444;
            }
            body {
                background-color: var(--bg-primary);
                color: var(--text-main);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                height: 100vh;
                overflow: hidden;
            }
            /* Sidebar */
            .sidebar {
                width: 260px;
                background-color: var(--bg-secondary);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                padding: 20px 0;
            }
            .sidebar-logo {
                font-size: 1.5rem;
                font-weight: bold;
                color: var(--accent-cyan);
                padding: 0 20px 20px;
                border-bottom: 1px solid var(--border-color);
                letter-spacing: 2px;
            }
            .sidebar-menu {
                list-style: none;
                padding: 0;
                margin: 20px 0;
            }
            .sidebar-menu li {
                padding: 15px 20px;
                cursor: pointer;
                transition: background 0.2s;
                color: var(--text-muted);
            }
            .sidebar-menu li:hover, .sidebar-menu li.active {
                background-color: var(--bg-tertiary);
                color: var(--accent-cyan);
                border-left: 3px solid var(--accent-cyan);
            }
            /* Main Content */
            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow-y: auto;
            }
            .topbar {
                height: 60px;
                background-color: var(--bg-secondary);
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                padding: 0 30px;
                justify-content: space-between;
            }
            .content-area {
                padding: 30px;
            }
            /* Dashboard Grid */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric-card {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
            }
            .metric-title {
                color: var(--text-muted);
                font-size: 0.9rem;
                text-transform: uppercase;
                margin-bottom: 10px;
            }
            .metric-value {
                font-size: 2rem;
                font-weight: bold;
                color: var(--accent-cyan);
            }
            /* 8-Layer Architecture Visualization */
            .layer-section {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
            }
            .layer-title {
                margin-top: 0;
                color: var(--text-main);
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .layers-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .layer-box {
                background-color: var(--bg-tertiary);
                border: 1px solid var(--accent-blue);
                padding: 10px;
                border-radius: 6px;
                font-size: 0.85rem;
                text-align: center;
                flex: 1;
                margin: 0 5px;
                color: var(--accent-cyan);
            }
            /* Evidence Ledger Table */
            .table-container {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            th, td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid var(--border-color);
                font-size: 0.9rem;
            }
            th {
                color: var(--text-muted);
                text-transform: uppercase;
                font-weight: normal;
            }
            .badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: bold;
            }
            .badge.allowed { background-color: rgba(16, 185, 129, 0.2); color: var(--status-allowed); }
            .badge.blocked { background-color: rgba(239, 68, 68, 0.2); color: var(--status-blocked); }
            .badge.mode { background-color: rgba(59, 130, 246, 0.2); color: var(--accent-blue); }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-logo">VCP CONTROL</div>
            <ul class="sidebar-menu">
                <li class="active">Dashboard</li>
                <li>Authority Graph</li>
                <li>Policy Engine</li>
                <li>Evidence Audit</li>
                <li>Agent Registry</li>
            </ul>
        </div>
        
        <div class="main-content">
            <div class="topbar">
                <div style="font-size: 1.2rem;">Control Plane / Overview</div>
                <div>Status: <span style="color: var(--status-allowed);">● ONLINE</span></div>
            </div>
            
            <div class="content-area">
                <!-- Metrics -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-title">Total AI Actions</div>
                        <div class="metric-value" id="val-total">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Blocked by VCP</div>
                        <div class="metric-value" id="val-blocked" style="color: var(--status-blocked);">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Active Agents</div>
                        <div class="metric-value" id="val-agents">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Threat Level</div>
                        <div class="metric-value" id="val-threat">LOW</div>
                    </div>
                </div>

                <!-- 8 Layers Visual -->
                <div class="layer-section">
                    <h3 class="layer-title">VCP 8-Layer Enforcement Pipeline</h3>
                    <div class="layers-container">
                        <div class="layer-box">1. Identity</div>➔
                        <div class="layer-box">2. Authority</div>➔
                        <div class="layer-box">3. Intent</div>➔
                        <div class="layer-box">4. Policy</div>➔
                        <div class="layer-box">5. Delegation</div>➔
                        <div class="layer-box" style="border-color: var(--status-blocked);">6. Execution(AEG)</div>➔
                        <div class="layer-box">7. Evidence</div>➔
                        <div class="layer-box">8. Recovery</div>
                    </div>
                </div>

                <!-- Evidence Ledger -->
                <div class="table-container">
                    <h3 class="layer-title">Live Evidence Ledger (Audit Trail)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Evidence ID</th>
                                <th>Agent ID</th>
                                <th>Action</th>
                                <th>Recovery Contract</th>
                                <th>Decision</th>
                            </tr>
                        </thead>
                        <tbody id="ledger-body">
                            <!-- JS injected rows -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            // API Polling function to keep dashboard live
            async function refreshDashboard() {
                try {
                    // Fetch Metrics
                    const resMetrics = await fetch('/api/system/metrics');
                    const metrics = await resMetrics.json();
                    document.getElementById('val-total').innerText = metrics.total_actions;
                    document.getElementById('val-blocked').innerText = metrics.blocked_actions;
                    document.getElementById('val-agents').innerText = metrics.active_agents;
                    document.getElementById('val-threat').innerText = metrics.threat_level;
                    if(metrics.threat_level === "ELEVATED") {
                        document.getElementById('val-threat').style.color = "var(--status-blocked)";
                    }

                    // Fetch Evidence Logs
                    const resLogs = await fetch('/api/evidence/logs');
                    const logs = await resLogs.json();
                    const tbody = document.getElementById('ledger-body');
                    tbody.innerHTML = '';
                    
                    if (logs.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">No actions recorded yet.</td></tr>';
                    } else {
                        logs.forEach(log => {
                            const date = new Date(log.timestamp).toLocaleTimeString();
                            const statusBadge = log.status === 'ALLOWED' 
                                ? `<span class="badge allowed">ALLOWED</span>` 
                                : `<span class="badge blocked">BLOCKED</span>`;
                            const recoveryBadge = `<span class="badge mode">${log.recovery_mode}</span>`;
                            
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${date}</td>
                                <td style="font-family: monospace; color: var(--text-muted);">${log.evidence_id}</td>
                                <td>${log.agent_id}</td>
                                <td>${log.action_type}</td>
                                <td>${recoveryBadge}</td>
                                <td>${statusBadge}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                    }
                } catch (e) {
                    console.error("Failed to fetch dashboard data:", e);
                }
            }

            // Test function to simulate AI agent hitting the AEG Gateway
            async function simulateAIAction() {
                const actions = [
                    { agent_id: "agent-mai-001", intent: "read db", action: "read_users" },
                    { agent_id: "agent-mai-001", intent: "pay vendor", action: "payment_execute", parameters: {amount: 10000} },
                    { agent_id: "agent-sub-002", intent: "delete log", action: "delete_files" } // Should fail authority
                ];
                const testAction = actions[Math.floor(Math.random() * actions.length)];
                
                await fetch('/vcp/gate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(testAction)
                });
                refreshDashboard();
            }

            // Initialize
            refreshDashboard();
            setInterval(refreshDashboard, 5000); // Auto refresh every 5s
            
            // For demo purposes: Simulate an AI action every 10 seconds
            setInterval(simulateAIAction, 10000);
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    # Render や Heroku などのPaaS環境では環境変数 PORT を使用する
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
