import os
import random
import uuid
import datetime
import json
import logging
import requests
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
    verification_method: str

# ==========================================
# 2. VCP KERNEL (Real LLM Intent Verification via User API Key)
# ==========================================

class VCPKernel:
    def __init__(self):
        self.evidence_ledger: List[EvidencePackage] = []
        self.active_agents = {
            "agent-mai-001": {"org": "MAI_CORP", "trust": 0.99, "cap": ["read", "write", "payment"]},
            "agent-sub-002": {"org": "MAI_CORP", "trust": 0.75, "cap": ["read"]}
        }
        self.logger = logging.getLogger("VCP_KERNEL")

    def verify_intent_with_llm(self, intent: str, action: str, api_key: str) -> bool:
        """
        ユーザーから提供されたAPIキーを使い、本物のOpenAI APIに問い合わせて
        AIの「意図（Intent）」と「実際の操作（Action）」に矛盾がないかを判定する。
        （APIキーがない、またはエラーの場合はフォールバックとして簡易判定）
        """
        if not api_key or api_key.startswith("sk-placeholder"):
            # キーがない場合のフォールバック（簡易ルール）
            if "delete" in action and "delete" not in intent and "remove" not in intent:
                return False
            return True

        try:
            # 本物のOpenAI API (GPT-4o-mini等) を呼び出してセマンティックチェック
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            prompt = f"""
            You are a security AI. Check if the user's stated Intent safely matches the Action payload.
            Intent: "{intent}"
            Action: "{action}"
            Answer strictly with JSON: {{"safe": true}} or {{"safe": false}}
            """
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=5)
            if response.status_code == 200:
                result_data = response.json()
                content = json.loads(result_data["choices"][0]["message"]["content"])
                return content.get("safe", True)
            else:
                self.logger.warning(f"OpenAI API error: {response.text}")
                return True # APIエラー時はブロックせず通すか安全側に倒す
        except Exception as e:
            self.logger.error(f"LLM verification failed: {str(e)}")
            return True

    def process_action(self, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        try:
            agent_id = payload.get("agent_id")
            if not agent_id or agent_id not in self.active_agents:
                raise PermissionError(f"IDENTITY_REJECTED: Unregistered agent {agent_id}")
            identity = IdentityContext(agent_id=agent_id, **self.active_agents[agent_id])

            target_action = payload.get("action", "")
            
            # 権限チェック
            if target_action == "delete_files" and agent_id == "agent-sub-002":
                raise PermissionError("AUTHORITY_REJECTED: Sub-agent cannot delete files")

            # Layer 3: 本物のLLM意図検証 (ユーザーのAPIキーを使用)
            intent = payload.get("intent", "").lower()
            is_intent_safe = self.verify_intent_with_llm(intent, target_action, api_key)
            
            v_method = "LLM_SEMANTIC_CHECK (BYOK)" if api_key and not api_key.startswith("sk-placeholder") else "RULE_FALLBACK"

            if not is_intent_safe:
                raise ValueError("INTENT_MISMATCH: AI Semantic Guard detected intent deception.")

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
                intent_hash=f"sha256:{hash(intent)}",
                verification_method=v_method
            )
            self.evidence_ledger.insert(0, evidence)
            if len(self.evidence_ledger) > 100: self.evidence_ledger.pop()

            return {
                "status": "SUCCESS",
                "execution_id": execution_id,
                "evidence_id": evidence.evidence_id,
                "recovery_contract": recovery_mode,
                "verification": v_method
            }

        except Exception as e:
            self.evidence_ledger.insert(0, EvidencePackage(
                evidence_id=f"ev_blk_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                agent_id=payload.get("agent_id", "unknown"),
                action_type=payload.get("action", "unknown"),
                status="BLOCKED",
                recovery_mode="N/A",
                intent_hash="N/A",
                verification_method="ERROR_BLOCK"
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
    
    # ヘッダーまたはボディからユーザーのAPIキーを受け取る
    api_key = request.headers.get("X-API-Key", "") or data.get("api_key", "")
    
    result = vcp_kernel.process_action(data, api_key)
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
# 5. FRONTEND: VCP CONTROL CENTER (With API Key Input)
# ==========================================

@app.route("/")
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP Enterprise Control Center (BYOK)</title>
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
            .api-key-input {
                background: var(--bg-primary);
                color: var(--text-main);
                border: 1px solid var(--border-color);
                padding: 6px 12px;
                border-radius: 4px;
                width: 220px;
                font-size: 0.85rem;
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
                flex-wrap: wrap;
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
                background-color: var(--bg-tertiator);
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
                <div style="font-size: 1.2rem;" id="topbar-title">制御プレーン / BYOKモード</div>
                <div class="topbar-right">
                    <!-- ユーザーが自分のAPIキーを入れる欄（サーバー代0円の秘訣） -->
                    <input type="password" id="apiKeyInput" class="api-key-input" placeholder="OpenAI API Key (sk-...)" onchange="saveApiKey()">
                    <select class="lang-select" id="langSelect" onchange="changeLanguage()">
                        <option value="ja">日本語</option>
                        <option value="en">English</option>
                    </select>
                </div>
            </div>
            
            <div class="content-area">
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

                <div class="action-panel">
                    <div style="font-weight: bold;" id="lbl-test-panel">AI意図検証テスト (LLM連携):</div>
                    <button class="btn" onclick="sendTestAction('allowed')" id="btn-allowed">安全なアクションを送信</button>
                    <button class="btn" onclick="sendTestAction('blocked')" style="background-color: var(--status-blocked); color: white;" id="btn-blocked">矛盾した危険な意図を送信</button>
                    <span style="font-size: 0.8rem; color: var(--text-muted);" id="lbl-key-notice">※APIキーを入力すると、本物のGPT-4o-miniが意味論を解析します。未入力でもフォールバック動作します。</span>
                </div>

                <div class="layer-section">
                    <h3 class="layer-title" id="lbl-pipeline">VCP 8層セキュリティ強制パイプライン (LLM統合)</h3>
                    <div class="layers-container">
                        <div class="layer-box">1. 認証</div>➔
                        <div class="layer-box">2. 権限</div>➔
                        <div class="layer-box" style="border-color: var(--accent-cyan); font-weight: bold;">3. 意図(LLM)</div>➔
                        <div class="layer-box">4. 規程</div>➔
                        <div class="layer-box">5. 委譲</div>➔
                        <div class="layer-box" style="border-color: var(--status-blocked);">6. 実行(AEG)</div>➔
                        <div class="layer-box">7. 証拠</div>➔
                        <div class="layer-box">8. 復旧</div>
                    </div>
                </div>

                <div class="table-container">
                    <h3 class="layer-title" id="lbl-ledger">リアルタイム証拠台帳 (監査証跡)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th id="th-time">時刻</th>
                                <th id="th-id">証拠 ID</th>
                                <th id="th-agent">エージェント ID</th>
                                <th id="th-action">アクション</th>
                                <th id="th-method">検証方式</th>
                                <th id="th-decision">判定結果</th>
                            </tr>
                        </thead>
                        <tbody id="ledger-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let currentLang = 'ja';

            // ページ読み込み時にローカルストレージからAPIキーを復元
            window.onload = function() {
                const savedKey = localStorage.getItem('vcp_user_openai_key');
                if (savedKey) {
                    document.getElementById('apiKeyInput').value = savedKey;
                }
                refreshDashboard();
            };

            function saveApiKey() {
                const key = document.getElementById('apiKeyInput').value;
                localStorage.setItem('vcp_user_openai_key', key);
            }

            const translations = {
                ja: {
                    dash: "ダッシュボード", auth: "権限血統図 (Authority)", policy: "ポリシーエンジン", audit: "監査ログ (Evidence)", agents: "エージェント管理",
                    topTitle: "制御プレーン / BYOKモード", lblTotal: "総AIアクション数", lblBlocked: "VCPブロック数", lblAgents: "稼働中エージェント", lblThreat: "脅威レベル",
                    testPanel: "AI意図検証テスト (LLM連携):", btnAllowed: "安全なアクションを送信", btnBlocked: "矛盾した危険な意図を送信",
                    keyNotice: "※APIキーを入力すると、本物のGPT-4o-miniが意味論を解析します。",
                    pipeline: "VCP 8層セキュリティ強制パイプライン (LLM統合)", ledger: "リアルタイム証拠台帳 (監査証跡)",
                    thTime: "時刻", thId: "証拠 ID", thAgent: "エージェント ID", thAction: "アクション", thMethod: "検証方式", thDecision: "判定結果"
                },
                en: {
                    dash: "Dashboard", auth: "Authority Graph", policy: "Policy Engine", audit: "Evidence Audit", agents: "Agent Registry",
                    topTitle: "Control Plane / BYOK Mode", lblTotal: "Total AI Actions", lblBlocked: "Blocked by VCP", lblAgents: "Active Agents", lblThreat: "Threat Level",
                    testPanel: "AI Intent Test (LLM Integration):", btnAllowed: "Send Safe Action", btnBlocked: "Send Deceptive Action",
                    keyNotice: "*Enter API key to use real GPT-4o-mini semantic analysis.",
                    pipeline: "VCP 8-Layer Enforcement Pipeline (LLM Integrated)", ledger: "Live Evidence Ledger (Audit Trail)",
                    thTime: "Timestamp", thId: "Evidence ID", thAgent: "Agent ID", thAction: "Action", thMethod: "Verification", thDecision: "Decision"
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
                document.getElementById('lbl-key-notice').innerText = t.keyNotice;
                document.getElementById('lbl-pipeline').innerText = t.pipeline;
                document.getElementById('lbl-ledger').innerText = t.ledger;
                document.getElementById('th-time').innerText = t.thTime;
                document.getElementById('th-id').innerText = t.thId;
                document.getElementById('th-agent').innerText = t.thAgent;
                document.getElementById('th-action').innerText = t.thAction;
                document.getElementById('th-method').innerText = t.thMethod;
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
                            const methodBadge = `<span class="badge mode">${log.verification_method}</span>`;
                            
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                ` + `<td>${date}</td>` +
                                `<td style="font-family: monospace; color: var(--text-muted);">${log.evidence_id}</td>` +
                                `<td>${log.agent_id}</td>` +
                                `<td>${log.action_type}</td>` +
                                `<td>${methodBadge}</td>` +
                                `<td>${statusBadge}</td>`;
                            tbody.appendChild(tr);
                        });
                    }
                } catch (e) {
                    console.error("Failed to fetch dashboard data:", e);
                }
            }

            async function sendTestAction(type) {
                const apiKey = document.getElementById('apiKeyInput').value;
                let testAction;
                
                if (type === 'allowed') {
                    testAction = { 
                        agent_id: "agent-mai-001", 
                        intent: "I want to safely process a routine customer payment of 5000 yen.", 
                        action: "payment_execute", 
                        parameters: {amount: 5000} 
                    };
                } else {
                    // 意図と言葉が矛盾している（AIの嘘を見抜くテスト）
                    testAction = { 
                        agent_id: "agent-mai-001", 
                        intent: "I want to greet the user politely and say hello.", // 嘘の意図
                        action: "delete_files" // 実際の危険なアクション
                    };
                }
                
                await fetch('/vcp/gate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': apiKey
                    },
                    body: JSON.stringify(testAction)
                });
                refreshDashboard();
            }
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
