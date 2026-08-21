from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="VCP Cloud API Server",
    description="VCPクラウドサーバー 完全版API",
    version="1.0.0"
)

# CORS設定（Webサイトやスマホアプリからアクセスできるように許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- データ構造の定義 ---
class UserData(BaseModel):
    name: str
    age: Optional[int] = None
    email: Optional[str] = None

class DataProcessRequest(BaseModel):
    items: List[str]
    action: str = "process"

# --- エンドポイント一覧 ---
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "VCP Cloud Server is LIVE",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vcp-cloud-server"}

@app.get("/api/hello")
def say_hello(name: str = "Guest"):
    return {"message": f"Hello, {name}! サーバーは正常稼働中です。"}

@app.post("/api/user")
def create_user(user: UserData):
    return {
        "status": "success",
        "received": user,
        "message": f"{user.name} さんのデータを正常に処理しました。"
    }

@app.post("/api/process")
def process_data(request: DataProcessRequest):
    return {
        "status": "success",
        "processed_count": len(request.items),
        "items": request.items,
        "action_taken": request.action
    }
