import sqlite3
import json
import uuid
import datetime
from flask import Flask, jsonify, request

DB_PATH = "vcp_main.db"

def init_vcp_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Identity & Capability Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents 
                      (agent_id TEXT PRIMARY KEY, capabilities TEXT)''')
    
    # 2. Policy Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                      (policy_id TEXT PRIMARY KEY, target_action TEXT, max_amount REAL)''')
    
    # 初期データ投入 (テスト用エージェントとポリシー)
    cursor.execute("INSERT OR REPLACE INTO agents VALUES (?, ?)", 
                   ("agent-001", json.dumps(["transfer", "read"])))
    cursor.execute("INSERT OR REPLACE INTO policies VALUES (?, ?, ?)", 
                   ("pol-limit-001", "transfer", 1000.0))
    
    conn.commit()
    conn.close()

class VCPCore:
    def __init__(self):
        init_vcp_db()

    def process(self, payload):
        agent_id = payload.get("agent_id")
        action = payload.get("action")
        amount = payload.get("amount", 0)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # 1. Identity / Capability Check
            cursor.execute("SELECT capabilities FROM agents WHERE agent_id = ?", (agent_id,))
            agent = cursor.fetchone()
            
            if not agent:
                return {"status": "BLOCKED", "reason": "IDENTITY_NOT_FOUND"}
            
            caps = json.loads(agent[0])
            if action not in caps:
                return {"status": "BLOCKED", "reason": "CAPABILITY_VIOLATION"}

            # 2. Policy Check
            cursor.execute("SELECT max_amount FROM policies WHERE target_action = ?", (action,))
            policy = cursor.fetchone()
            if policy and amount > policy[0]:
                return {"status": "BLOCKED", "reason": "POLICY_VIOLATION_LIMIT_EXCEEDED"}

            return {"status": "ALLOWED", "reason": "PASS_DETERMINISTIC_CHECK"}

        finally:
            conn.close()

app = Flask(__name__)
vcp = VCPCore()

@app.route("/vcp/gate", methods=["POST"])
def gate():
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON payload"}), 400
    return jsonify(vcp.process(data))

if __name__ == "__main__":
    print("--- VCP ENTERPRISE CORE (Phase 1) STARTED ---")
    app.run(host="127.0.0.1", port=5000, debug=False)
