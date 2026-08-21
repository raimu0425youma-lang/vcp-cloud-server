import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>VCP CLOUD SYSTEM - ONLINE</title>
    <style>
        body { background: #030712; color: #f8fafc; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: #0f172a; border: 1px solid #334155; padding: 30px; border-radius: 12px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
        h1 { color: #06b6d4; font-size: 20px; margin-bottom: 10px; }
        p { color: #94a3b8; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>VCP SYSTEM ONLINE</h1>
        <p>サーバーは正常に稼働しています。接続成功！</p>
    </div>
</body>
</html>"""

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
