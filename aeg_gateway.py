from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

app = FastAPI()

# 自分のAPIキーをここに入れる
GEMINI_API_KEY = "AIzaSyAomLvoL0BxKIxAoQq6eJtsA9bexCWj024"

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    try:
        body = await request.json()
        
        # モデル名を最新版に変更
        body["model"] = "gemini-1.5-flash-latest"
        
        response = client.chat.completions.create(**body)
        return response.model_dump()
    except Exception as e:
        print(f"[AEG ERROR] {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "aeg_status": "GEMINI_ERROR",
                "error_detail": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aeg_gateway:app", host="0.0.0.0", port=8000, reload=True)