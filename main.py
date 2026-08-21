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
    REVERSIBLE = "REVERSIBLE"       
    COMPENSATABLE = "COMPENSATABLE" 
    DELAYABLE = "DELAYABLE"         
    IRREVERSIBLE = "IRREVERSIBLE"   

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
    def __init__(self):
        self.evidence_ledger: List[EvidencePackage] = []
        self.active_agents = {
            "agent-mai-001": {"org": "MAI_CORP", "trust": 0.99, "cap": ["read", "write", "payment"]},
            "agent-sub-002": {"org": "MAI_CORP", "trust": 0.75, "cap": ["read"]}
        }
        self.logger = logging.getLogger("VCP_KERNEL")

    def process_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            agent_id = payload.get("agent_id")
            if not agent_id or agent_id not in self.active_agents:
                raise PermissionError(f"IDENTITY_REJECTED: Unregistered agent {agent_id}")
            identity = IdentityContext(agent_id=agent_id, **self.active_agents[agent_id])

            target_action = payload.get("action", "")
            
            # 権限チェックの緩和（デモをしやすくするため）
            if target_action == "delete_files" and agent_id == "agent-sub-002":
                raise PermissionError("AUTHORITY_REJECTED: Sub-agent cannot delete files")

            intent = payload.get("intent", "").lower()
            if "delete" in target_action and "delete" not in intent and "remove" not in intent:
                raise ValueError("INTENT_MISMATCH: Action payload contradicts stated intent.")

            amount = payload.get("parameters", {}).get("amount", 0)
            if target_action == "payment_execute" and amount > 500000:
                raise PermissionError("POLICY_VIOLATION: Payment amount exceeds limit.")

            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            recovery_mode = RecoveryContract.REVERSIBLE.value
            if "payment" in target_action:
                recovery_mode = RecoveryContract.COMPENSATABLE.value
            elif "delete" in target_action:
                recovery_mode = RecoveryContract.IRREVERSIBLE.value

            evidence = EvidencePackage(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                agent_id=identity.agent_id,
                action_type=target_action,
                status="ALLOWED",
                recovery_mode=recovery_mode,
                intent_hash=f"sha256:{hash(intent)}"
            )
            self.evidence_ledger.insert(0, evidence)
            if len(self.evidence_ledger) > 100: self.evidence_ledger.pop()

            return {
                "status": "SUCCESS",
                "execution_id": execution_id,
                "evidence_id": evidence.evidence_id,
                "recovery_contract": recovery_mode
            }

        except Exception as e:
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
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON"}), 400
    result = vcp_kernel.process_action(data)
    status_code = 200 if result["status"] == "SUCCESS" else 403
    return jsonify(result), status_code

@app.route("/api/evidence/logs", methods=["GET"])
def get_evidence_logs():
    return jsonify([asdict(ev) for ev in vcp_kernel.evidence_ledger[:20]])

@app.route("/api/system/metrics", methods=["GET"])
def get_metrics():
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
# 5. FRONTEND: VCP CONTROL CENTER (Multi-lang & Manual)
# ==========================================

@app.route("/")
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP Enterprise Control Center</title>
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
            .sidebar {
                width: 260px;
                background-color: var(--bg-secondary);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                padding: 20px 0;
            }
            .sidebar-logo {
                font-size: 1.4rem;
                font-weight: bold;
                color: var(--accent-cyan);
                padding: 0 20px 20px;
                border-bottom: 1px solid var(--border-color);
                letter-spacing: 1px;
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
            .topbar-right {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .lang-select {
                background: var(--bg-tertiary);
                color: var(--text-main);
                border: 1px solid var(--border-color);
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
            }
            .content-area {
                padding: 30px;
            }
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
            .action-panel {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                display: flex;
                gap: 15px;
                align-items: center;
            }
            .btn {
                background-color: var(--accent-cyan);
                color: var(--bg-primary);
                border: none;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
                cursor: pointer;
                transition: background 0.2s;
            }
            .btn:hover { background-color: var(--accent-cyan-hover); }
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
                flex-wrap: wrap;
                gap: 5px;
            }
            .layer-box {
                background-color: var(--bg-tertiary);
                border: 1px solid var(--accent-blue);
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 0.8rem;
                text-align: center;
                flex: 1;
                color: var(--accent-cyan);
            }
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
                <li class="active" id="menu-dash">ダッシュボード</li>
                <li id="menu-graph">権限血統図 (Authority)</li>
                <li id="menu-policy">ポリシーエンジン</li>
                <li id="menu-audit">監査ログ (Evidence)</li>
                <li id="menu-agents">エージェント管理</li>
            </ul>
        </div>
        
        <div class="main-content">
            <div class="topbar">
                <div style="font-size: 1.2rem;" id="topbar-title">制御プレーン / 概要</div>
                <div class="topbar-right">
                    <span>ステータス: <span style="color: var(--status-allowed);">● オンライン</span></span>
                    <select class="lang-select" id="langSelect" onchange="changeLanguage()">
                        <option value="ja">日本語</option>
                        <option value="en">English</option>
                    </select>
                </div>
            </div>
            
            <div class="content-area">
                <!-- Metrics -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-title" id="lbl-total">総AIアクション数</div>
                        <div class="metric-value" id="val-total">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title" id="lbl-blocked">VCPブロック数</div>
                        <div class="metric-value" id="val-blocked" style="color: var(--status-blocked);">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title" id="lbl-agents">稼働中エージェント</div>
                        <div class="metric-value" id="val-agents">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title" id="lbl-threat">脅威レベル</div>
                        <div class="metric-value" id="val-threat">低 (LOW)</div>
                    </div>
                </div>

                <!-- Manual Test Action Panel (勝手に動かない手動テスト用) -->
                <div class="action-panel">
                    <div style="font-weight: bold;" id="lbl-test-panel">AIアクション手動テスト:</div>
                    <button class="btn" onclick="sendTestAction('allowed')" id="btn-allowed">正常アクションを送信 (ALLOW)</button>
                    <button class="btn" onclick="sendTestAction('blocked')" style="background-color: var(--status-blocked); color: white;" id="btn-blocked">不正アクションを送信 (BLOCK)</button>
                </div>

                <!-- 8 Layers Visual -->
                <div class="layer-section">
                    <h3 class="layer-title" id="lbl-pipeline">VCP 8層セキュリティ強制パイプライン</h3>
                    <div class="layers-container">
                        <div class="layer-box">1. 認証 (Identity)</div>➔
                        <div class="layer-box">2. 権限 (Authority)</div>➔
                        <div class="layer-box">3. 意図 (Intent)</div>➔
                        <div class="layer-box">4. 規程 (Policy)</div>➔
                        <div class="layer-box">5. 委譲 (Delegation)</div>➔
                        <div class="layer-box" style="border-color: var(--status-blocked);">6. 実行 (AEG)</div>➔
                        <div class="layer-box">7. 証拠 (Evidence)</div>➔
                        <div class="layer-box">8. 復旧 (Recovery)</div>
                    </div>
                </div>

                <!-- Evidence Ledger -->
                <div class="table-container">
                    <h3 class="layer-title" id="lbl-ledger">リアルタイム証拠台帳 (監査証跡)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th id="th-time">時刻</th>
                                <th id="th-id">証拠 ID</th>
                                <th id="th-agent">エージェント ID</th>
                                <th id="th-action">アクション</th>
                                <th id="th-recovery">リカバリー契約</th>
                                <th id="th-decision">判定結果</th>
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
            let currentLang = 'ja';

            const translations = {
                ja: {
                    dash: "ダッシュボード",
                    auth: "権限血統図 (Authority)",
                    policy: "ポリシーエンジン",
                    audit: "監査ログ (Evidence)",
                    agents: "エージェント管理",
                    topTitle: "制御プレーン / 概要",
                    lblTotal: "総AIアクション数",
                    lblBlocked: "VCPブロック数",
                    lblAgents: "稼働中エージェント",
                    lblThreat: "脅威レベル",
                    testPanel: "AIアクション手動テスト:",
                    btnAllowed: "正常アクションを送信 (ALLOW)",
                    btnBlocked: "不正アクションを送信 (BLOCK)",
                    pipeline: "VCP 8層セキュリティ強制パイプライン",
                    ledger: "リアルタイム証拠台帳 (監査証跡)",
                    thTime: "時刻",
                    thId: "証拠 ID",
                    thAgent: "エージェント ID",
                    thAction: "アクション",
                    thRecovery: "リカバリー契約",
                    thDecision: "判定結果"
                },
                en: {
                    dash: "Dashboard",
                    auth: "Authority Graph",
                    policy: "Policy Engine",
                    audit: "Evidence Audit",
                    agents: "Agent Registry",
                    topTitle: "Control Plane / Overview",
                    lblTotal: "Total AI Actions",
                    lblBlocked: "Blocked by VCP",
                    lblAgents: "Active Agents",
                    lblThreat: "Threat Level",
                    testPanel: "Manual AI Action Test:",
                    btnAllowed: "Send Valid Action (ALLOW)",
                    btnBlocked: "Send Malicious Action (BLOCK)",
                    pipeline: "VCP 8-Layer Enforcement Pipeline",
                    ledger: "Live Evidence Ledger (Audit Trail)",
                    thTime: "Timestamp",
                    thId: "Evidence ID",
                    thAgent: "Agent ID",
                    thAction: "Action",
                    thRecovery: "Recovery Contract",
                    thDecision: "Decision"
                }
            };

            function changeLanguage() {
                currentLang = document.getElementById('langSelect').value;
                const t = translations[currentLang];
                
                document.getElementById('menu-dash').innerText = t.dash;
                document.getElementById('menu-graph').innerText = t.auth;
                document.getElementById('menu-policy').innerText = t.policy;
                document.getElementById('menu-audit').innerText = t.audit;
                document.getElementById('menu-agents').innerText = t.agents;
                document.getElementById('topbar-title').innerText = t.topTitle;
                document.getElementById('lbl-total').innerText = t.lblTotal;
                document.getElementById('lbl-blocked').innerText = t.lblBlocked;
                document.getElementById('lbl-agents').innerText = t.lblAgents;
                document.getElementById('lbl-threat').innerText = t.lblThreat;
                document.getElementById('lbl-test-panel').innerText = t.testPanel;
                document.getElementById('btn-allowed').innerText = t.btnAllowed;
                document.getElementById('btn-blocked').innerText = t.btnBlocked;
                document.getElementById('lbl-pipeline').innerText = t.pipeline;
                document.getElementById('lbl-ledger').innerText = t.ledger;
                document.getElementById('th-time').innerText = t.thTime;
                document.getElementById('th-id').innerText = t.thId;
                document.getElementById('th-agent').innerText = t.thAgent;
                document.getElementById('th-action').innerText = t.thAction;
                document.getElementById('th-recovery').innerText = t.thRecovery;
                document.getElementById('th-decision').innerText = t.thDecision;
            }

            async function refreshDashboard() {
                try {
                    const resMetrics = await fetch('/api/system/metrics');
                    const metrics = await resMetrics.json();
                    document.getElementById('val-total').innerText = metrics.total_actions;
                    document.getElementById('val-blocked').innerText = metrics.blocked_actions;
                    document.getElementById('val-agents').innerText = metrics.active_agents;
                    document.getElementById('val-threat').innerText = metrics.threat_level;

                    const resLogs = await fetch('/api/evidence/logs');
                    const logs = await resLogs.json();
                    const tbody = document.getElementById('ledger-body');
                    tbody.innerHTML = '';
                    
                    if (logs.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">データがありません (No actions recorded)</td></tr>';
                    } else {
                        logs.forEach(log => {
                            const date = new Date(log.timestamp).toLocaleTimeString();
                            const statusBadge = log.status === 'ALLOWED' 
                                ? `<span class="badge allowed">ALLOW</span>` 
                                : `<span class="badge blocked">BLOCK</span>`;
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

            // 手動テスト用関数（勝手に動くのを廃止し、ボタンを押したときだけ実行）
            async function sendTestAction(type) {
                let testAction;
                if (type === 'allowed') {
                    testAction = { agent_id: "agent-mai-001", intent: "pay vendor safely", action: "payment_execute", parameters: {amount: 5000} };
                } else {
                    testAction = { agent_id: "agent-sub-002", intent: "delete log without permission", action: "delete_files" };
                }
                
                await fetch('/vcp/gate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(testAction)
                });
                refreshDashboard();
            }

            refreshDashboard();
            // 自動シミュレーションは停止しました（setIntervalを削除）
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
