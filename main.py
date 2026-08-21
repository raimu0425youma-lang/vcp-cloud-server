import os
import sqlite3
import json
import hashlib
import datetime
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')
DB_PATH = "vcp_main.db"

def init_vcp_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 1. Identity & Capability Grid
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY)''')
    # 2. Authority Graph / Delegation Firewall
    cursor.execute('''CREATE TABLE IF NOT EXISTS delegations 
                      (id INTEGER PRIMARY KEY, grantor TEXT, grantee TEXT, permission TEXT, active INTEGER)''')
    # 3. Policy & Multi-tier Thresholds
    cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                      (permission TEXT PRIMARY KEY, max_amount REAL, approval_threshold REAL)''')
    # 4. Immutable Evidence Chain (Tamper-evident audit log)
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
    
    # 初期エンタープライズデータ構築 (Root -> 001 -> 002 -> 003)
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('root')")
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('agent-001')")
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('agent-002')")
    cursor.execute("INSERT OR REPLACE INTO agents VALUES ('agent-003')")
    
    cursor.execute("INSERT OR REPLACE INTO delegations (grantor, grantee, permission, active) VALUES ('root', 'agent-001', 'transfer', 1)")
    cursor.execute("INSERT OR REPLACE INTO delegations (grantor, grantee, permission, active) VALUES ('agent-001', 'agent-002', 'transfer', 1)")
    cursor.execute("INSERT OR REPLACE INTO delegations (grantor, grantee, permission, active) VALUES ('agent-002', 'agent-003', 'transfer', 1)")
    
    # ポリシー設定: 自動許可 1000以下 / 人間承認 1000〜10000 / 絶対ブロック 10000超
    cursor.execute("INSERT OR REPLACE INTO policies VALUES ('transfer', 1000.0, 10000.0)")
    conn.commit()
    conn.close()

init_vcp_db()

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

def trace_authority_graph(grantee, permission, visited=None):
    """再帰的グラフ走査による委譲チェーンの検証と無限ループ防止"""
    if visited is None:
        visited = set()
    if grantee in visited:
        return []
    visited.add(grantee)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT grantor FROM delegations WHERE grantee = ? AND permission = ? AND active = 1", (grantee, permission))
    rows = cursor.fetchall()
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
    """暗号学的ハッシュチェーンによる改ざん不能な証跡の生成"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT current_hash FROM evidence_chain ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    prev_hash = last_row[0] if last_row else "0" * 64

    timestamp = datetime.datetime.utcnow().isoformat()
    raw_data = f"{timestamp}|{grantee}|{action}|{amount}|{status}|{reason}|{prev_hash}"
    current_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

    cursor.execute("""
        INSERT INTO evidence_chain (timestamp, grantee, action, amount, status, reason, prev_hash, current_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, grantee, action, amount, status, reason, prev_hash, current_hash))
    
    conn.commit()
    conn.close()
    return current_hash

@app.route("/vcp/gate", methods=["POST"])
def gate():
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "reason": "Invalid JSON payload"}), 400

    grantee = data.get("agent_id")
    action = data.get("action")
    amount = data.get("amount", 0)
    
    # [Phase 7 Extension Hook] BYOK (Bring Your Own Key) & Semantic AI Audit
    user_api_key = data.get("byok_api_key")
    if user_api_key:
        # ユーザー自身のAPIキーを用いたLLMセマンティック検証をここに挟む拡張構造
        pass

    # 1. Authority Graph 追跡 (Delegation Firewall)
    valid_paths = trace_authority_graph(grantee, action)
    if not valid_paths:
        h = record_evidence(grantee, action, amount, "BLOCKED", "AUTHORITY_GRAPH_DISCONNECTED")
        return jsonify({
            "status": "BLOCKED", 
            "reason": "AUTHORITY_GRAPH_DISCONNECTED",
            "evidence_hash": h
        })

    # 2. Policy & Multi-tier Human Approval Check
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT max_amount, approval_threshold FROM policies WHERE permission = ?", (action,))
    policy = cursor.fetchone()
    conn.close()

    if policy:
        max_amt = policy[0]
        approval_thresh = policy[1]

        if amount > approval_thresh:
            h = record_evidence(grantee, action, amount, "BLOCKED", "POLICY_VIOLATION_CRITICAL_LIMIT")
            return jsonify({
                "status": "BLOCKED", 
                "reason": "CRITICAL_LIMIT_EXCEEDED_ABSOLUTE_BLOCK",
                "evidence_hash": h
            })
        elif amount > max_amt:
            h = record_evidence(grantee, action, amount, "HUMAN_APPROVAL", "EXCEEDS_AUTO_LIMIT_PENDING_ADMIN")
            return jsonify({
                "status": "HUMAN_APPROVAL", 
                "reason": "REQUIRES_MANAGEMENT_SIGN_OFF",
                "verified_chain": valid_paths,
                "evidence_hash": h
            })

    # 3. ALLOWED
    h = record_evidence(grantee, action, amount, "ALLOWED", "AUTHORITY_GRAPH_VERIFIED")
    return jsonify({
        "status": "ALLOWED", 
        "reason": "AUTHORITY_GRAPH_VERIFIED",
        "verified_chain": valid_paths,
        "evidence_hash": h
    })

@app.route("/vcp/audit/verify", methods=["GET"])
def verify_audit_chain():
    """監査証跡の整合性を完全リプレイ検証するフォレンジック機能"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, grantee, action, amount, status, reason, prev_hash, current_hash FROM evidence_chain ORDER BY id ASC")
    rows = cursor.fetchall()
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
