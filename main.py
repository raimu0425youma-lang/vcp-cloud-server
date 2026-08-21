import os
import sqlite3
import json
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')
DB_PATH = "vcp_main.db"

def init_vcp_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 1. Agents (Identity)
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY)''')
    # 2. Delegations (Authority Graph: 誰が、誰に、何を渡したか)
    cursor.execute('''CREATE TABLE IF NOT EXISTS delegations 
                      (id INTEGER PRIMARY KEY, grantor TEXT, grantee TEXT, permission TEXT, active INTEGER)''')
    # 3. Policies (Limit)
    cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                      (permission TEXT PRIMARY KEY, max_amount REAL)''')
    
    # Setup: root -> agent-001 -> agent-002 という委譲チェーンを作る
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('root')")
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('agent-001')")
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('agent-002')")
    
    # rootがagent-001にtransferを委譲
    cursor.execute("INSERT OR REPLACE INTO delegations (grantor, grantee, permission, active) VALUES ('root', 'agent-001', 'transfer', 1)")
    # agent-001がagent-002にtransferを委譲 (再委譲)
    cursor.execute("INSERT OR REPLACE INTO delegations (grantor, grantee, permission, active) VALUES ('agent-001', 'agent-002', 'transfer', 1)")
    
    cursor.execute("INSERT OR REPLACE INTO policies VALUES ('transfer', 1000.0)")
    conn.commit()
    conn.close()

init_vcp_db()

@app.route("/")
def index(): return send_from_directory('.', 'index.html')

@app.route("/vcp/gate", methods=["POST"])
def gate():
    data = request.get_json()
    grantee = data.get("agent_id")
    action = data.get("action")
    amount = data.get("amount", 0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delegation Check (再帰的または直接的な権限確認)
    # ここでは単純化のため「誰かからそのアクションを許可されているか」をチェック
    cursor.execute("SELECT grantor FROM delegations WHERE grantee = ? AND permission = ? AND active = 1", (grantee, action))
    has_permission = cursor.fetchone()
    
    if not has_permission:
        return jsonify({"status": "BLOCKED", "reason": "NO_DELEGATED_AUTHORITY"})

    # Policy Check
    cursor.execute("SELECT max_amount FROM policies WHERE permission = ?", (action,))
    policy = cursor.fetchone()
    if policy and amount > policy[0]:
        return jsonify({"status": "BLOCKED", "reason": "POLICY_VIOLATION_LIMIT_EXCEEDED"})

    return jsonify({"status": "ALLOWED", "reason": f"DELEGATED_AUTHORITY_VERIFIED_FROM_{has_permission[0]}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
