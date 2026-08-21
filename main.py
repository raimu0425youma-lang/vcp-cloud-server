from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="VCP Cloud Ultimate Engine",
    description="VCPクラウド 完全統合システム（最終決定版）",
    version="2.0.0"
)

# 通信許可設定 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# メモリ内データベース
db_items = []
analytics_data = [
    {"id": 1, "category": "売上", "amount": 12000, "note": "初期設定データA", "time": "12:00:00"},
    {"id": 2, "category": "開発", "amount": 5000, "note": "初期設定データB", "time": "13:00:00"},
]

# --- データモデル定義 ---
class UserData(BaseModel):
    name: str
    age: Optional[int] = None

class ItemData(BaseModel):
    title: str
    detail: Optional[str] = ""

class MetricInput(BaseModel):
    category: str
    amount: float
    note: Optional[str] = ""

# --- フロントエンド（統合フルUIダッシュボード） ---
@app.get("/", response_class=HTMLResponse)
def root_ui():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP Cloud Ultimate Console</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090d16; color: #f1f5f9; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid #1e293b; margin-bottom: 24px; }
            .header h1 { margin: 0; font-size: 24px; color: #38bdf8; }
            .badge { background: #064e3b; color: #34d399; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #059669; }
            .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
            @media (max-width: 900px) { .grid-3, .grid-2 { grid-template-columns: 1fr; } }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
            .card h3 { margin-top: 0; font-size: 16px; color: #94a3b8; border-bottom: 1px solid #1f2937; padding-bottom: 10px; margin-bottom: 16px; }
            .stat-box { background: #1f2937; padding: 16px; border-radius: 8px; text-align: center; }
            .stat-num { font-size: 22px; font-weight: bold; color: #38bdf8; }
            .stat-lbl { font-size: 12px; color: #9ca3af; margin-top: 4px; }
            input, select, textarea, button { width: 100%; padding: 10px; margin-top: 8px; border-radius: 6px; border: 1px solid #374151; background: #1f2937; color: #fff; font-size: 14px; box-sizing: border-box; outline: none; }
            button { background: #0284c7; font-weight: bold; cursor: pointer; border: none; transition: 0.2s; }
            button:hover { background: #0369a1; }
            .btn-danger { background: #dc2626; padding: 4px 8px; font-size: 12px; width: auto; margin: 0; }
            .btn-danger:hover { background: #b91c1c; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #1f2937; }
            th { background: #1f2937; color: #9ca3af; }
            .log-box { background: #000; border: 1px solid #1f2937; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #4ade80; min-height: 48px; word-break: break-all; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>VCP Cloud 統合コントロールパネル</h1>
                <span class="badge">● 全システム正常稼働中</span>
            </div>

            <!-- 1. 統計サマリー -->
            <div class="grid-3">
                <div class="stat-box"><div class="stat-num" id="totalAmount">¥0</div><div class="stat-lbl">集計データ総計</div></div>
                <div class="stat-box"><div class="stat-num" id="itemCount">0 件</div><div class="stat-lbl">保存済みメモ・タスク</div></div>
                <div class="stat-box"><div class="stat-num" id="apiStatus">200 OK</div><div class="stat-lbl">API通信ステータス</div></div>
            </div>

            <!-- 2. データ入力 & グラフ分析 -->
            <div class="grid-2">
                <div class="card">
                    <h3>📊 データ・数値登録（グラフ連動）</h3>
                    <select id="anCategory">
                        <option value="売上">売上</option>
                        <option value="開発">開発費</option>
                        <option value="マーケ">広告費</option>
                        <option value="その他">その他</option>
                    </select>
                    <input type="number" id="anAmount" placeholder="金額 / 数値">
                    <input type="text" id="anNote" placeholder="メモ">
                    <button onclick="addAnalytics()">送信してグラフ更新</button>
                </div>
                <div class="card">
                    <h3>📈 リアルタイムデータ分析グラフ</h3>
                    <canvas id="analyticsChart" height="160"></canvas>
                </div>
            </div>

            <!-- 3. データベース & APIテスト -->
            <div class="grid-2">
                <div class="card">
                    <h3>📝 データベース管理（メモ・タスク）</h3>
                    <input type="text" id="dbTitle" placeholder="タイトル">
                    <textarea id="dbDetail" placeholder="詳細テキスト" rows="2"></textarea>
                    <button onclick="addDbItem()">クラウドへ保存</button>
                    
                    <div style="margin-top: 15px; max-height: 200px; overflow-y: auto;">
                        <table>
                            <thead><tr><th>タイトル</th><th>詳細</th><th>操作</th></tr></thead>
                            <tbody id="dbTableBody"></tbody>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <h3>⚡ ユーザー送信 / API疎通テスト</h3>
                    <input type="text" id="usrName" placeholder="名前を入力">
                    <input type="number" id="usrAge" placeholder="年齢を入力">
                    <button onclick="sendUserApi()">/api/user (POST) を実行</button>
                    <div class="log-box" id="apiLog">レスポンス結果がここに表示されます</div>
                </div>
            </div>
        </div>

        <script>
            let chartInstance = null;

            // 初期化読み込み
            async function init() {
                await loadAnalytics();
                await loadDbItems();
            }

            // アナリティクス取得 & グラフ描画
            async function loadAnalytics() {
                const res = await fetch('/api/analytics');
                const data = await res.json();
                
                const total = data.reduce((sum, d) => sum + d.amount, 0);
                document.getElementById('totalAmount').innerText = '¥' + total.toLocaleString();

                const categories = {};
                data.forEach(d => categories[d.category] = (categories[d.category] || 0) + d.amount);

                if (chartInstance) chartInstance.destroy();
                const ctx = document.getElementById('analyticsChart').getContext('2d');
                chartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(categories),
                        datasets: [{ data: Object.values(categories), backgroundColor: ['#38bdf8', '#818cf8', '#f43f5e', '#fbbf24'] }]
                    },
                    options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } } }
                });
            }

            async function addAnalytics() {
                const category = document.getElementById('anCategory').value;
                const amount = parseFloat(document.getElementById('anAmount').value);
                const note = document.getElementById('anNote').value;
                if (isNaN(amount)) return alert('数値を入力してください');

                await fetch('/api/analytics', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category, amount, note })
                });
                document.getElementById('anAmount').value = '';
                document.getElementById('anNote').value = '';
                loadAnalytics();
            }

            // データベース CRUD
            async function loadDbItems() {
                const res = await fetch('/api/items');
                const data = await res.json();
                document.getElementById('itemCount').innerText = data.length + ' 件';

                const tbody = document.getElementById('dbTableBody');
                if(data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#6b7280;">データはありません</td></tr>';
                    return;
                }
                tbody.innerHTML = data.map(item => `
                    <tr>
                        <td><b>${item.title}</b></td>
                        <td style="color:#9ca3af;">${item.detail || '-'}</td>
                        <td><button class="btn-danger" onclick="deleteDbItem(${item.id})">削除</button></td>
                    </tr>
                `).join('');
            }

            async function addDbItem() {
                const title = document.getElementById('dbTitle').value;
                const detail = document.getElementById('dbDetail').value;
                if (!title) return alert('タイトルを入力してください');

                await fetch('/api/items', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, detail })
                });
                document.getElementById('dbTitle').value = '';
                document.getElementById('dbDetail').value = '';
                loadDbItems();
            }

            async function deleteDbItem(id) {
                await fetch('/api/items/' + id, { method: 'DELETE' });
                loadDbItems();
            }

            // API送信テスト
            async function sendUserApi() {
                const name = document.getElementById('usrName').value || 'ゲスト';
                const age = parseInt(document.getElementById('usrAge').value) || 20;
                const log = document.getElementById('apiLog');
                log.innerText = "通信中...";

                try {
                    const res = await fetch('/api/user', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, age })
                    });
                    const data = await res.json();
                    log.innerText = JSON.stringify(data, null, 2);
                } catch(e) {
                    log.innerText = "通信エラーが発生しました";
                }
            }

            init();
        </script>
    </body>
    </html>
    """

# --- バックエンドAPI群 ---
@app.get("/health")
def health():
    return {"status": "ok", "system": "VCP Cloud Complete Engine"}

@app.get("/api/hello")
def say_hello(name: str = "Guest"):
    return {"message": f"Hello, {name}! VCP Cloud Serverは正常稼働中です。"}

@app.post("/api/user")
def create_user(user: UserData):
    return {
        "status": "success",
        "message": f"【登録完了】{user.name}さん（{user.age or '未設定'}歳）のデータを受信しました。"
    }

@app.get("/api/items")
def get_items():
    return db_items

@app.post("/api/items")
def add_item(item: ItemData):
    new_item = {
        "id": len(db_items) + 1,
        "title": item.title,
        "detail": item.detail,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db_items.append(new_item)
    return {"status": "success", "item": new_item}

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    global db_items
    db_items = [i for i in db_items if i["id"] != item_id]
    return {"status": "success"}

@app.get("/api/analytics")
def get_analytics():
    return analytics_data

@app.post("/api/analytics")
def add_analytics(metric: MetricInput):
    new_id = max([a["id"] for a in analytics_data], default=0) + 1
    new_entry = {
        "id": new_id,
        "category": metric.category,
        "amount": metric.amount,
        "note": metric.note,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    analytics_data.append(new_entry)
    return {"status": "success", "entry": new_entry}
