from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from vcp_core.src.schema import ActionProposal, AuthorizationResult, ExecutionRequest, ExecutionEvidence
from vcp_core.src.authority import VCPAuthorityEngine

app = FastAPI(title="VCP CORE Authority Gateway")
engine = VCPAuthorityEngine()

@app.post("/propose", response_model=AuthorizationResult)
def propose_action(proposal: ActionProposal):
    return engine.authorize_proposal(proposal)

@app.post("/execute")
def execute_action(req: ExecutionRequest):
    success, msg, evidence = engine.execute_action(req)
    if not success:
        raise HTTPException(status_code=403, detail=msg)
    return {"message": msg, "evidence": evidence}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>VCP CORE - Authority & Delegation Gateway</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; }
            .card { background-color: #161b22; border: 1px solid #30363d; }
            .token-box { word-break: break-all; font-size: 0.75rem; color: #58a6ff; }
        </style>
    </head>
    <body class="p-4">
        <div class="container-fluid">
            <h2>🛡️ <b>VCP CORE</b> <span class="badge bg-warning text-dark">Authority Gateway</span></h2>
            <p class="text-secondary">Identity ➔ Delegation ➔ Authority ➔ Token ➔ Execution ➔ Evidence</p>
            <hr class="border-secondary">

            <div class="row">
                <div class="col-md-5">
                    <div class="card p-3 mb-3">
                        <h5 class="text-info">1. 行為提案 (/propose)</h5>
                        <div class="mb-2"><label>Human Owner ID:</label><input id="human" class="form-control bg-dark text-white border-secondary" value="usr_ceo_01"></div>
                        <div class="mb-2"><label>Agent ID (子AI):</label><input id="agent" class="form-control bg-dark text-white border-secondary" value="agent_purchasing_99"></div>
                        <div class="mb-2"><label>Target Resource:</label><input id="resource" class="form-control bg-dark text-white border-secondary" value="aws_ec2"></div>
                        <div class="mb-2"><label>Action:</label><input id="action" class="form-control bg-dark text-white border-secondary" value="create_instance"></div>
                        <div class="mb-2"><label>申請金額 (円):</label><input id="amount" type="number" class="form-control bg-dark text-white border-secondary" value="40000"></div>
                        
                        <div class="p-2 border border-secondary rounded mb-2 bg-black">
                            <small class="text-warning">Delegation Chain (権限減衰設定):</small>
                            <div style="font-size: 0.8rem;">
                                CEO ➔ Finance (上限: 100,000円)<br>
                                Finance ➔ Purchasing Agent (上限: 50,000円)
                            </div>
                        </div>
                        
                        <button onclick="sendProposal()" class="btn btn-primary w-100 fw-bold">権限検証 ＆ トークン発行 (/propose)</button>
                    </div>

                    <div class="card p-3">
                        <h5 class="text-success">2. 権限実行 (/execute)</h5>
                        <div class="mb-2">
                            <label>発行済み ExecutionToken:</label>
                            <div id="token_display" class="token-box p-2 border border-secondary rounded bg-black">未発行</div>
                        </div>
                        <button onclick="executeAction()" id="exec_btn" class="btn btn-success w-100 fw-bold" disabled>安全実行ゲートウェイを通過 (/execute)</button>
                    </div>
                </div>

                <div class="col-md-7">
                    <div class="card p-3">
                        <h5 class="text-warning">📋 実行結果 ＆ 証跡 (Proof)</h5>
                        <pre id="output" class="bg-black p-3 text-white border border-secondary rounded" style="min-height: 400px; font-size: 0.85rem;">待機中...</pre>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentToken = null;

            async function sendProposal() {
                const payload = {
                    human_owner_id: document.getElementById('human').value,
                    agent_id: document.getElementById('agent').value,
                    target_resource: document.getElementById('resource').value,
                    proposed_action: document.getElementById('action').value,
                    requested_amount: parseFloat(document.getElementById('amount').value),
                    delegation_chain: [
                        { delegation_id: "del_ceo_to_fin", parent_agent_id: "agent_ceo", child_agent_id: "agent_finance", max_sub_budget: 100000, allowed_resources: ["aws_ec2", "db_refund"] },
                        { delegation_id: "del_fin_to_pur", parent_agent_id: "agent_finance", child_agent_id: "agent_purchasing_99", max_sub_budget: 50000, allowed_resources: ["aws_ec2"] }
                    ]
                };

                const res = await fetch('/propose', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                document.getElementById('output').innerText = JSON.stringify(data, null, 2);

                if (data.authorized) {
                    currentToken = data.execution_token;
                    document.getElementById('token_display').innerText = currentToken;
                    document.getElementById('exec_btn').disabled = false;
                } else {
                    currentToken = null;
                    document.getElementById('token_display').innerText = "拒否されました";
                    document.getElementById('exec_btn').disabled = true;
                }
            }

            async function executeAction() {
                if (!currentToken) return;

                const res = await fetch('/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        execution_token: currentToken,
                        action_payload: { timestamp: Date.now() }
                    })
                });

                const data = await res.json();
                document.getElementById('output').innerText = JSON.stringify(data, null, 2);
            }
        </script>
    </body>
    </html>
    """
