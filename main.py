import os
import sqlite3
import json
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

DB_PATH = "vcp_main.db"

def init_vcp_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY, capabilities TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, target_action TEXT, max_amount REAL)''')
    cursor.execute("INSERT OR REPLACE INTO agents VALUES (?, ?)", ("agent-001", json.dumps(["transfer", "read"])))
    cursor.execute("INSERT OR REPLACE INTO policies VALUES (?, ?, ?)", ("pol-limit-001", "transfer", 1000.0))
    conn.commit()
    conn.close()

# 起動時にDB初期化
init_vcp_db()

@app.route("/")
def index():
    # ルートURLにアクセスがあったら index.html を返す
    return send_from_directory('.', 'index.html')

@app.route("/vcp/gate", methods=["POST"])
def gate():
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON payload"}), 400
    
    agent_id = data.get("agent_id")
    action = data.get("action")
    amount = data.get("amount", 0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT capabilities FROM agents WHERE agent_id = ?", (agent_id,))
        agent = cursor.fetchone()
        if not agent:
            return jsonify({"status": "BLOCKED", "reason": "IDENTITY_NOT_FOUND"})
        
        caps = json.loads(agent[0])
        if action not in caps:
            return jsonify({"status": "BLOCKED", "reason": "CAPABILITY_VIOLATION"})

        cursor.execute("SELECT max_amount FROM policies WHERE target_action = ?", (action,))
        policy = cursor.fetchone()
        if policy and amount > policy[0]:
            return jsonify({"status": "BLOCKED", "reason": "POLICY_VIOLATION_LIMIT_EXCEEDED"})

        return jsonify({"status": "ALLOWED", "reason": "PASS_DETERMINISTIC_CHECK"})
    finally:
        conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
