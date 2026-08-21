from fastapi import FastAPI

app = FastAPI(title="VCP Cloud API")

@app.get("/")
def read_root():
    return {"status": "online", "message": "VCP Cloud Server is LIVE"}

@app.get("/api/hello")
def say_hello(name: str = "Guest"):
    return {"message": f"Hello, {name}! クラウドサーバーの更新に成功しました！"}
