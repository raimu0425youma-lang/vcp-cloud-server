from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="VCP Cloud All-In-One System",
    description="VCPクラウド 全機能統合完全版",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース（メモリ保持）
db_items = []
analytics_data = [
    {"id": 1, "category": "売上", "amount": 15000, "note": "初期データA", "time": "12:00:00"},
    {"id": 2, "category": "開発", "amount": 8000, "note": "初期データB", "time": "13:00:00"},
]

# モデル定義
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

class CalcRequest(BaseModel):
    initial: float
    monthly: float
    rate: float
    years: int

class AiRequest(BaseModel):
    prompt: str

# 統合フロントエンド画面
@app.get("/", response_class=HTMLResponse)
def root_ui():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP All-In-One Control Center</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #080c14; color: #f1f5f9; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid #1e293b; margin-bottom: 24px; }
            .header h1 { margin: 0; font-size: 24px; color: #38bdf8; }
            .badge { background: #064e3b; color: #34d399; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #059669; }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
            @media (max-width: 850px) { .grid-2 { grid-template-columns: 1fr; } }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
            .card h3 { margin-top: 0; font-size: 16px; color: #38bdf8; border-bottom: 1px solid #1f2937; padding-bottom: 10px; margin-bottom: 14px; }
            input, select, textarea, button { width: 100%; padding: 10px; margin-top: 6px; margin-bottom: 6px; border-radius: 6px; border: 1px solid #374151; background: #1f2937; color: #fff; font-size: 13px; box-sizing: border-box; outline: none; }
            button { background: #0284c7; font-weight: bold; cursor: pointer; border: none; transition: 0.2s; margin-top: 10px; }
            button:hover { background: #0369a1; }
            .btn-del { background: #dc2626; padding: 4px 8px; font-size: 11px; width: auto; margin: 0; }
            .btn-del:hover { background: #b91c1c; }
            .res-box { background: #030712; border: 1px solid #1f2937; padding: 10px; border-radius: 6px; color: #4ade80; font-size: 13px; margin-top: 8px; min-height: 40px; word-break: break-all; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #1f2937; }
            th { background: #1f2937; color: #9ca3af; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>VCP クラウド全機能統合コントロールセンター</h1>
                <span class="badge">● 全システム稼働中</span>
            </div>

            <!-- Row 1: 資産シミュレーター & AIエンジン -->
            <div class="grid-2">
                <div class="card">
                    <h3>📈 資産運用複利シミュレーター</h3>
                    <input type="number" id="calcInit" placeholder="初期投資 (万円)" value="100">
                    <input type="number" id="calcMonth" placeholder="毎月積立 (万円)" value="5">
                    <input type="number" id="calcRate" placeholder="想定年利 (%)" value="7">
                    <input type="number" id="calcYears" placeholder="運用期間 (年)" value="15">
                    <button onclick="runCalc()">将来資産を試算</button>
                    <div class="res-box" id="calcRes">ここに計算結果が表示されます</div>
                </div>

                <div class="card">
                    <h3>🤖 サーバーAI処理エンジン</h3>
                    <textarea id="aiPrompt" rows="5" placeholder="質問や指示を入力..."></textarea>
                    <button onclick="runAi()">AI処理を実行</button>
                    <div class="res-box" id="aiRes" style="color:#e2e8f0;">回答待機中...</div>
                </div>
            </div>

            <!-- Row 2: リアルタイム分析 & グラフ -->
            <div class="grid-2">
                <div class="card">
                    <h3>📊 リアルタイムデータ集計・入力</h3>
                    <select id="anCat">
                        <option value="売上">売上</option>
                        <option value="開発">開発費</option>
                        <option value="マーケ">広告費</option>
                        <option value="その他">その他</option>
                    </select>
                    <input type="number" id="anAmt" placeholder="金額 / 数値">
                    <input type="text" id="anNote" placeholder="メモ">
                    <button onclick="addAnalytics()">送信してグラフ更新</button>
                </div>

                <div class="card">
                    <h3>📉 カテゴリ別割合グラフ</h3>
                    <canvas id="chartCanvas" height="150"></canvas>
                </div>
            </div>

            <!-- Row 3: データベース管理 & APIテスト -->
            <div class="grid-2">
                <div class="card">
                    <h3>📝 クラウドデータベース（メモ保存）</h3>
                    <input type="text" id="dbTitle" placeholder="タイトル">
                    <input type="text" id="dbDetail" placeholder="詳細メモ">
                    <button onclick="addDb()">保存する</button>
                    <div style="margin-top:10px; max-height:150px; overflow-y:auto;">
                        <table>
                            <thead><tr><th>タイトル</th><th>詳細</th><th>操作</th></tr></thead>
                            <tbody id="dbTbody"></tbody>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <h3>⚡ ユーザー登録 API疎通テスト</h3>
                    <input type="text" id="usrName" placeholder="名前">
                    <input type="number" id="usrAge" placeholder="年齢">
                    <button onclick="sendUser()">/api/user (POST) 送信</button>
                    <div class="res-box" id="usrRes">レスポンスログが表示されます</div>
                </div>
            </div>
        </div>

        <script>
            let myChart = null;

            async function init() {
                loadAnalytics();
                loadDb();
            }

            // 複利計算
            async function runCalc() {
                const initial = parseFloat(document.getElementById('calcInit').value) || 0;
                const monthly = parseFloat(document.getElementById('calcMonth').value) || 0;
                const rate = parseFloat(document.getElementById('calcRate').value) || 0;
                const years = parseInt(document.getElementById('calcYears').value) || 0;

                const res = await fetch('/api/calc', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({initial, monthly, rate, years})
                });
                const data = await res.json();
                document.getElementById('calcRes').innerText = data.result_text;
            }

            // AIレスポンス
            async function runAi() {
                const prompt = document.getElementById('aiPrompt').value;
                if(!prompt) return alert('テキストを入力してください');
                document.getElementById('aiRes').innerText = '処理中...';
                const res = await fetch('/api/ai', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({prompt})
                });
                const data = await res.json();
                document.getElementById('aiRes').innerText = data.reply;
            }

            // アナリティクス & グラフ
            async function loadAnalytics() {
                const res = await fetch('/api/analytics');
                const data = await res.json();
                const categories = {};
                data.forEach(d => categories[d.category] = (categories[d.category] || 0) + d.amount);

                if (myChart) myChart.destroy();
                const ctx = document.getElementById('chartCanvas').getContext('2d');
                myChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(categories),
                        datasets: [{ data: Object.values(categories), backgroundColor: ['#38bdf8', '#818cf8', '#f43f5e', '#fbbf24'] }]
                    },
                    options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } } }
                });
            }

            async function addAnalytics() {
                const category = document.getElementById('anCat').value;
                const amount = parseFloat(document.getElementById('anAmt').value);
                const note = document.getElementById('anNote').value;
                if(isNaN(amount)) return alert('数値を入力してください');

                await fetch('/api/analytics', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({category, amount, note})
                });
                document.getElementById('anAmt').value = '';
                document.getElementById('anNote').value = '';
                loadAnalytics();
            }

            // データベース CRUD
            async function loadDb() {
                const res = await fetch('/api/items');
                const data = await res.json();
                const tbody = document.getElementById('dbTbody');
                tbody.innerHTML = data.map(item => `
                    <tr>
                        <td><b>${item.title}</b></td>
                        <td style="color:#9ca3af;">${item.detail || '-'}</td>
                        <td><button class="btn-del" onclick="delDb(${item.id})">削除</button></td>
                    </tr>
                `).join('');
            }

            async function addDb() {
                const title = document.getElementById('dbTitle').value;
                const detail = document.getElementById('dbDetail').value;
                if(!title) return alert('タイトルを入力してください');

                await fetch('/api/items', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({title, detail})
                });
                document.getElementById('dbTitle').value = '';
                document.getElementById('dbDetail').value = '';
                loadDb();
            }

            async function delDb(id) {
                await fetch('/api/items/' + id, { method: 'DELETE' });
                loadDb();
            }

            // ユーザー通信テスト
            async function sendUser() {
                const name = document.getElementById('usrName').value || 'ゲスト';
                const age = parseInt(document.getElementById('usrAge').value) || 20;
                const res = await fetch('/api/user', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({name, age})
                });
                const data = await res.json();
                document.getElementById('usrRes').innerText = data.message;
            }

            init();
        </script>
    </body>
    </html>
    """

# --- バックエンドAPI ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/hello")
def say_hello(name: str = "Guest"):
    return {"message": f"Hello, {name}!"}

@app.post("/api/user")
def create_user(user: UserData):
    return {"status": "success", "message": f"【送信成功】{user.name}さん（{user.age or '未設定'}歳）のデータを受信しました。"}

@app.get("/api/items")
def get_items():
    return db_items

@app.post("/api/items")
def add_item(item: ItemData):
    new_item = {"id": len(db_items) + 1, "title": item.title, "detail": item.detail}
    db_items.append(new_item)
    return {"status": "success"}

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
    analytics_data.append({"id": new_id, "category": metric.category, "amount": metric.amount, "note": metric.note})
    return {"status": "success"}

@app.post("/api/calc")
def calculate(req: CalcRequest):
    r = (req.rate / 100) / 12
    months = req.years * 12
    future_initial = req.initial * ((1 + r) ** months) if r > 0 else req.initial
    future_monthly = req.monthly * (((1 + r) ** months - 1) / r) if r > 0 else req.monthly * months
    total = round(future_initial + future_monthly, 1)
    principal = round(req.initial + (req.monthly * months), 1)
    return {"status": "success", "result_text": f"{req.years}年後の想定資産: 約 {total:,.1f} 万円 (元本: {principal:,.1f}万円)"}

@app.post("/api/ai")
def ai_process(req: AiRequest):
    return {"status": "success", "reply": f"【クラウドAI受信完了】 「{req.prompt.strip()}」 のリクエストを正常に処理しました。"}
