import os
import random
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- バックエンド API エンドポイント ---

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>MAI ENTERPRISE CLOUD - GLOBAL CONTROL</title>
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
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        body { background-color: var(--bg-primary); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }

        /* サイドバー */
        .sidebar { width: 280px; background-color: var(--bg-secondary); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 24px; }
        .brand { font-size: 20px; font-weight: 800; color: var(--accent-cyan); letter-spacing: 1.5px; margin-bottom: 35px; display: flex; align-items: center; gap: 10px; }
        .brand::before { content: ''; display: block; width: 10px; height: 10px; background: var(--accent-cyan); border-radius: 50%; box-shadow: 0 0 10px var(--accent-cyan); }
        
        .nav-menu { list-style: none; display: flex; flex-direction: column; gap: 8px; flex: 1; }
        .nav-item { padding: 14px 18px; border-radius: 10px; color: var(--text-muted); cursor: pointer; transition: all 0.25s ease; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 12px; }
        .nav-item:hover, .nav-item.active { background-color: rgba(6, 182, 212, 0.12); color: var(--accent-cyan); border-left: 4px solid var(--accent-cyan); }

        .system-pill { padding: 14px; background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 10px; font-size: 12px; color: var(--success); text-align: center; font-weight: 600; }

        /* メインビュー */
        .main-wrapper { flex: 1; display: flex; flex-direction: column; background-color: var(--bg-primary); overflow: hidden; }
        .topbar { height: 70px; background-color: var(--bg-secondary); border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 35px; }
        .topbar-title { font-size: 16px; font-weight: 600; color: var(--text-main); }
        .user-badge { font-size: 13px; color: var(--text-muted); background: var(--bg-tertiary); padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border-color); }

        /* タブコンテンツエリア */
        .content-area { flex: 1; padding: 30px; overflow-y: auto; display: none; }
        .content-area.active { display: flex; flex-direction: column; gap: 20px; }

        /* チャットビュー特有のレイアウト */
        .chat-layout { display: flex; gap: 20px; height: 100%; }
        .chat-main { flex: 3; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; }
        .chat-messages { flex: 1; padding: 25px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
        .message { max-width: 80%; padding: 14px 18px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
        .message.ai { background-color: var(--bg-tertiary); color: var(--text-main); align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid var(--border-color); }
        .message.user { background-color: var(--accent-blue); color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
        .chat-input-box { padding: 20px; background: var(--bg-secondary); border-top: 1px solid var(--border-color); display: flex; gap: 12px; }
        .chat-input-box input { flex: 1; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px 18px; color: var(--text-main); font-size: 14px; outline: none; transition: border 0.2s; }
        .chat-input-box input:focus { border-color: var(--accent-cyan); }
        .btn-primary { background: var(--accent-cyan); color: var(--bg-primary); border: none; padding: 0 28px; border-radius: 10px; font-weight: 700; cursor: pointer; transition: background 0.2s; }
        .btn-primary:hover { background: var(--accent-cyan-hover); }

        /* サイドパネル（統計） */
        .chat-side { flex: 1; display: flex; flex-direction: column; gap: 20px; }
        .card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 14px; padding: 20px; }
        .card-title { font-size: 14px; font-weight: 700; color: var(--accent-cyan); margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; color: var(--text-muted); }
        .metric-val { color: var(--text-main); font-weight: 600; }

        /* その他のタブデザイン */
        .grid-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .stat-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 14px; padding: 24px; }
        .stat-label { font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }
        .stat-number { font-size: 28px; font-weight: 800; color: var(--text-main); }
        
        .log-container { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 14px; padding: 20px; flex: 1; font-family: monospace; font-size: 12px; color: var(--accent-cyan); overflow-y: auto; }
        .log-line { margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 4px; }
    </style>
</head>
<body>

    <!-- サイドバー -->
    <div class="sidebar">
        <div class="brand">MAI CORE v4.0</div>
        <ul class="nav-menu">
            <li class="nav-item active" onclick="switchTab('chat', this)">💬 ニューラルチャット</li>
            <li class="nav-item" onclick="switchTab('analytics', this)">📊 リアルタイム分析</li>
            <li class="nav-item" onclick="switchTab('logs', this)">🖥️ システムログ</li>
            <li class="nav-item" onclick="switchTab('settings', this)">⚙️ グローバル設定</li>
        </ul>
        <div class="system-pill">● サーバー稼働中 (99.99%)</div>
    </div>

    <!-- メインコンテンツ -->
    <div class="main-wrapper">
        <div class="topbar">
            <div class="topbar-title" id="topbarTitle">MAI Enterprise Neural Chatroom</div>
            <div class="user-badge">権限: スーパー管理者</div>
        </div>

        <!-- タブ1: チャット -->
        <div id="tab-chat" class="content-area active" style="height: calc(100vh - 70px);">
            <div class="chat-layout">
                <div class="chat-main">
                    <div class="chat-messages" id="chatBox">
                        <div class="message ai">MAIグローバル・ニューラルコアが起動しました。数百万ユーザー規模の同時処理スタンバイ完了。ご指示をどうぞ。</div>
                    </div>
                    <div class="chat-input-box">
                        <input type="text" id="userInput" placeholder="MAIへのコマンド、または質問を入力..." onkeypress="if(event.key==='Enter')sendChatMessage()">
                        <button class="btn-primary" onclick="sendChatMessage()">送信</button>
                    </div>
                </div>
                <div class="chat-side">
                    <div class="card">
                        <div class="card-title">リソース状況</div>
                        <div class="metric-row"><span>CPU負荷</span><span class="metric-val" id="cpuLoad">12.4%</span></div>
                        <div class="metric-row"><span>メモリ消費</span><span class="metric-val">1.8GB / 16GB</span></div>
                        <div class="metric-row"><span>アクティブスレッド</span><span class="metric-val">1,024</span></div>
                    </div>
                    <div class="card">
                        <div class="card-title">収益・スケーリング予測</div>
                        <div class="metric-row"><span>月間推定アクティブ</span><span class="metric-val">2,450,000人</span></div>
                        <div class="metric-row"><span>推定月商</span><span class="metric-val" style="color: var(--success);">￥184,500,000</span></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- タブ2: 分析 -->
        <div id="tab-analytics" class="content-area">
            <div class="grid-cards">
                <div class="stat-card">
                    <div class="stat-label">総リクエスト数 (本日の累計)</div>
                    <div class="stat-number">14,892,310</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">平均レスポンスタイム</div>
                    <div class="stat-number">12ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">エラー発生率</div>
                    <div class="stat-number" style="color: var(--success);">0.001%</div>
                </div>
            </div>
        </div>

        <!-- タブ3: ログ -->
        <div id="tab-logs" class="content-area" style="height: calc(100vh - 70px);">
            <div class="log-container" id="logBox">
                <div class="log-line">[2026-08-21 19:00:01] [INFO] MAI Engine initialized successfully.</div>
                <div class="log-line">[2026-08-21 19:00:05] [SECURITY] Global firewall rules applied.</div>
                <div class="log-line">[2026-08-21 19:00:12] [CLUSTER] Node cluster synchronized across 4 regions.</div>
            </div>
        </div>

        <!-- タブ4: 設定 -->
        <div id="tab-settings" class="content-area">
            <div class="card" style="max-width: 600px;">
                <div class="card-title">システム環境設定</div>
                <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">プラットフォーム全体の挙動やAIコアのパラメータを調整します。</p>
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div>
                        <label style="font-size: 13px; display: block; margin-bottom: 6px;">AIモデルモード</label>
                        <select style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-main); padding: 10px; border-radius: 8px;">
                            <option>MAI-Ultra-v4 (最高精度・大規模処理)</option>
                            <option>MAI-Turbo (超高速応答)</option>
                        </select>
                    </div>
                    <button class="btn-primary" style="padding: 12px; margin-top: 10px;" onclick="alert('設定が正常に保存されました。')">変更を適用</button>
                </div>
            </div>
        </div>

    </div>

    <script>
        function switchTab(tabName, element) {
            document.querySelectorAll('.content-area').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            document.getElementById('tab-' + tabName).classList.add('active');
            element.classList.add('active');

            const titles = {
                'chat': 'MAI Enterprise Neural Chatroom',
                'analytics': 'Real-time Global Analytics',
                'logs': 'System Core Audit Logs',
                'settings': 'Global System Configuration'
            };
            document.getElementById('topbarTitle').textContent = titles[tabName];
        }

        async function sendChatMessage() {
            const input = document.getElementById('userInput');
            const chatBox = document.getElementById('chatBox');
            const text = input.value.trim();
            if(!text) return;

            const userDiv = document.createElement('div');
            userDiv.className = 'message user';
            userDiv.textContent = text;
            chatBox.appendChild(userDiv);
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await response.json();

                const aiDiv = document.createElement('div');
                aiDiv.className = 'message ai';
                aiDiv.textContent = data.reply;
                chatBox.appendChild(aiDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            } catch (err) {
                const errDiv = document.createElement('div');
                errDiv.className = 'message ai';
                errDiv.textContent = "通信エラーが発生しました。バックエンドとの接続を確認してください。";
                chatBox.appendChild(errDiv);
            }
        }

        // 定期的にCPU負荷を擬似変動させる
        setInterval(() => {
            const load = (10 + Math.random() * 15).toFixed(1);
            const cpuEl = document.getElementById('cpuLoad');
            if(cpuEl) cpuEl.textContent = load + '%';
        }, 3000);
    </script>
</body>
</html>"""

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    user_msg = data.get("message", "")
    
    # 本格的なバックエンド処理のシミュレーション応答
    responses = [
        f"「{user_msg}」のリクエストを検知しました。マルチスレッド処理により最適化を実行中です。",
        f"データ解析完了：「{user_msg}」に基づくスケーリングプランを適用しました。順調に収益化ロジックが稼働しています。",
        f"了解いたしました。「{user_msg}」のシステム連携を確立します。数百万規模のトラフィックにも完全耐性があります。",
    ]
    reply = random.choice(responses)
    
    return jsonify({
        "status": "success",
        "reply": reply,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "system": "MAI Global Enterprise Core", "version": "4.0.0"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
