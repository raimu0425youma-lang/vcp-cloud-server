from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="VCP Cloud App")

class UserData(BaseModel):
    name: str
    age: Optional[int] = None

# --- アプリ画面（フロントエンド） ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VCP Cloud システム</title>
        <style>
            body { font-family: sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 32px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); width: 100%; max-width: 380px; text-align: center; border: 1px solid #334155; }
            h2 { color: #38bdf8; margin-top: 0; margin-bottom: 24px; font-size: 22px; }
            input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; font-size: 15px; outline: none; }
            input:focus { border-color: #38bdf8; }
            button { width: 100%; padding: 12px; margin-top: 16px; border-radius: 8px; border: none; background: #0284c7; color: white; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.2s; }
            button:hover { background: #0369a1; }
            #result { margin-top: 20px; padding: 12px; border-radius: 8px; background: #0f172a; font-weight: bold; color: #4ade80; min-height: 20px; word-break: break-all; border: 1px solid #334155; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>VCP クラウドコントロール</h2>
            <input type="text" id="nameInput" placeholder="名前を入力">
            <input type="number" id="ageInput" placeholder="年齢を入力">
            <button onclick="sendData()">送信する</button>
            <div id="result">待機中...</div>
        </div>

        <script>
            async function sendData() {
                const name = document.getElementById('nameInput').value || 'ゲスト';
                const age = parseInt(document.getElementById('ageInput').value) || 20;
                const resultDiv = document.getElementById('result');
                resultDiv.innerText = "送信中...";

                try {
                    const res = await fetch('/api/user', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name, age: age })
                    });
                    const data = await res.json();
                    resultDiv.innerText = data.message;
                } catch (err) {
                    resultDiv.innerText = "エラーが発生しました";
                }
            }
        </script>
    </body>
    </html>
    """

# --- 裏方の処理（バックエンド） ---
@app.post("/api/user")
def create_user(user: UserData):
    return {
        "status": "success",
        "message": f"【成功】{user.name}さん（{user.age}歳）のデータを受信しました！"
    }
