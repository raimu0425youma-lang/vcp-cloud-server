import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "system": "VCP Enterprise Core v3.0"})

@app.route("/api/ai/process", methods=["POST"])
def ai_process():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    return jsonify({"status": "success", "result": f"Processed: {prompt}"})

@app.route("/api/database/memo", methods=["POST"])
def save_memo():
    return jsonify({"status": "saved", "records": [{"title": "test", "detail": "test"}]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
