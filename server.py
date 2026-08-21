import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    if os.path.exists("static/index.html"):
        return send_file("static/index.html")
    return send_file("index.html")

@app.route("/popup.html")
def popup():
    if os.path.exists("static/popup.html"):
        return send_file("static/popup.html")
    return send_file("popup.html")

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "system": "VCP Enterprise Core v3.0"})

@app.route("/api/ai/process", methods=["POST"])
def ai_process():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    return jsonify({"status": "success", "result": f"Processed via API: {prompt}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
