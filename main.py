import os
import sqlite3
import json
import hashlib
import datetime
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

# PostgreSQL (Render) と SQLite (ローカル) の自動切り替え
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        conn = sqlite3.connect("vcp_main.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_vcp_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL用構文
        cursor.execute('''CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS delegations 
                          (id SERIAL PRIMARY KEY, grantor TEXT, grantee TEXT, permission TEXT, active INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                          (permission TEXT PRIMARY KEY, max_amount REAL, approval_threshold REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS evidence_chain 
                          (id SERIAL PRIMARY KEY, 
                           timestamp TEXT, 
                           grantee TEXT, 
                           action TEXT, 
                           amount REAL, 
                           status TEXT, 
                           reason TEXT, 
                           prev_hash TEXT, 
                           current_hash TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_keys 
                          (api_key TEXT PRIMARY KEY, owner TEXT, active INTEGER)''')
    else:
        # SQLite用構文
        cursor.execute('''CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS delegations 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, grantor TEXT, grantee TEXT, permission TEXT, active INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                          (permission TEXT PRIMARY KEY, max_amount REAL, approval_threshold REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS evidence_chain 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           timestamp TEXT, 
                           grantee TEXT, 
                           action TEXT, 
                           amount REAL, 
                           status TEXT, 
                           reason TEXT, 
                           prev_hash TEXT, 
                           current_hash TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_keys 
                          (api_key TEXT PRIMARY KEY, owner TEXT, active INTEGER)''')

    # 初期データ構築
    if DATABASE_URL:
        cursor.execute("INSERT INTO agents (agent_id) VALUES ('root') ON CONFLICT (agent_id) DO NOTHING")
        cursor.execute("INSERT INTO agents (agent_id) VALUES ('agent-001') ON CONFLICT (agent_id) DO NOTHING")
        cursor.execute("INSERT INTO agents (agent_id) VALUES ('agent-002') ON CONFLICT (agent_id) DO NOTHING")
        cursor.execute("INSERT INTO agents (agent_id) VALUES ('agent-003') ON CONFLICT (agent_id) DO NOTHING")
        
        cursor.execute("INSERT INTO policies (permission, max_amount, approval_threshold) VALUES ('transfer', 1000.0, 10000.0) ON CONFLICT (permission) DO NOTHING")
        cursor.execute("INSERT INTO api_keys (api_key, owner, active) VALUES ('vcp_live_secret_key_001', 'system_admin', 1) ON CONFLICT (api_key) DO NOTHING")
    else:
        cursor.execute("INSERT OR IGNORE INTO agents VALUES ('root')")
        cursor.execute("INSERT OR IGNORE INTO agents VALUES ('agent-001')")
        cursor.execute("INSERT OR IGNORE INTO agents VALUES ('agent-002')")
        cursor.execute("INSERT OR IGNORE INTO agents VALUES ('agent-003')")
        cursor.execute("INSERT OR IGNORE INTO policies VALUES ('transfer', 1000.0, 10000.0)")
        cursor.execute("INSERT OR IGNORE INTO api_keys VALUES ('vcp_live_secret_key_001', 'system_admin', 1)")

    conn.commit()
    cursor.close()
    conn.close()

init_vcp_db()

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

def trace_authority_graph(grantee, permission, visited=None):
    if visited is None:
        visited = set()
    if grantee in visited:
        return []
    visited.add(grantee)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT grantor FROM delegations WHERE grantee = ? AND permission = ? AND active = 1", (grantee, permission))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    paths = []
    for row in rows:
        grantor = row[0]
        if grantor == 'root':
            paths.append(['root', grantee])
        else:
            sub_paths = trace_authority_graph(grantor, permission, visited)
            for p in sub_paths:
                paths.append(p + [grantee])
    return paths

def record_evidence(grantee, action, amount, status, reason):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_hash FROM evidence_chain ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    cursor.close()
    
    prev_hash = last_row[0] if last_row else "0" * 64

    timestamp = datetime.datetime.utcnow().isoformat()
    raw_data = f"{timestamp}|{grantee}|{action}|{amount}|{status}|{reason}|{prev_hash}"
    current_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO evidence_chain (timestamp, grantee, action, amount, status, reason, prev_hash, current_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, grantee, action, amount, status, reason, prev_hash, current_hash))
    
    conn.commit()
    cursor.close()
    conn.close()
    return current_hash

@app.route("/vcp/gate", methods=["POST"])
def gate():
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON payload"}), 400

    # ステップ2: APIキー認証チェック
    client_api_key = data.get("api_key")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT active FROM api_keys WHERE api_key = ?", (client_api_key,))
    key_row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not key_row or key_row[0] != 1:
        return jsonify({"status": "BLOCKED", "reason": "INVALID_OR_MISSING_API_KEY"}), 401

    grantee = data.get("agent_id")
    action = data.get("action")
    amount = data.get("amount", 0)

    valid_paths = trace_authority_graph(grantee, action)
    if not valid_paths:
        h = record_evidence(grantee, action, amount, "BLOCKED", "AUTHORITY_GRAPH_DISCONNECTED")
        return jsonify({"status": "BLOCKED", "reason": "AUTHORITY_GRAPH_DISCONNECTED", "evidence_hash": h})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT max_amount, approval_threshold FROM policies WHERE permission = ?", (action,))
    policy = cursor.fetchone()
    cursor.close()
    conn.close()

    if policy:
        max_amt = policy[0]
        approval_thresh = policy[1]

        if amount > approval_thresh:
            h = record_evidence(grantee, action, amount, "BLOCKED", "POLICY_VIOLATION_CRITICAL_LIMIT")
            return jsonify({"status": "BLOCKED", "reason": "CRITICAL_LIMIT_EXCEEDED_ABSOLUTE_BLOCK", "evidence_hash": h})
        elif amount > max_amt:
            h = record_evidence(grantee, action, amount, "HUMAN_APPROVAL", "EXCEEDS_AUTO_LIMIT_PENDING_ADMIN")
            return jsonify({"status": "HUMAN_APPROVAL", "reason": "REQUIRES_MANAGEMENT_SIGN_OFF", "verified_chain": valid_paths, "evidence_hash": h})

    h = record_evidence(grantee, action, amount, "ALLOWED", "AUTHORITY_GRAPH_VERIFIED")
    return jsonify({"status": "ALLOWED", "reason": "AUTHORITY_GRAPH_VERIFIED", "verified_chain": valid_paths, "evidence_hash": h})

@app.route("/vcp/audit/verify", methods=["GET"])
def verify_audit_chain():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, grantee, action, amount, status, reason, prev_hash, current_hash FROM evidence_chain ORDER BY id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    expected_prev_hash = "0" * 64
    tampered = False
    audit_report = []

    for row in rows:
        r_id, timestamp, grantee, action, amount, status, reason, prev_hash, current_hash = row
        if prev_hash != expected_prev_hash:
            tampered = True

        raw_data = f"{timestamp}|{grantee}|{action}|{amount}|{status}|{reason}|{prev_hash}"
        recalculated_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

        if recalculated_hash != current_hash:
            tampered = True

        audit_report.append({
            "id": r_id,
            "integrity": "VALID" if not tampered else "COMPROMISED",
            "hash": current_hash
        })
        expected_prev_hash = current_hash

    return jsonify({
        "chain_status": "SECURE_AND_VERIFIED" if not tampered else "TAMPERING_DETECTED",
        "total_records": len(rows),
        "audit_trail": audit_report
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
