import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import FastAPI, Request, Response, Header
import httpx
from pydantic import BaseModel

app = FastAPI(title="Aegis Egress Gateway (AEG)")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

class ExpectedExtractionSchema(BaseModel):
    user_id: str
    action: str
    amount: float
    confidence: float

def generate_proof_log(request_body: dict, raw_response_text: str, error_detail: str) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    req_bytes = json.dumps(request_body, sort_keys=True).encode('utf-8')
    res_bytes = raw_response_text.encode('utf-8')
    
    req_hash = hashlib.sha256(req_bytes).hexdigest()
    res_hash = hashlib.sha256(res_bytes).hexdigest()
    
    proof_block = {
        "aeg_version": "0.2-fallback",
        "timestamp_utc": timestamp,
        "event_type": "SILENT_SCHEMA_FAILURE_AND_FALLBACK",
        "hashes": {
            "request_hash": req_hash,
            "response_hash": res_hash,
            "proof_signature": hashlib.sha256(f"{req_hash}:{res_hash}:{timestamp}".encode('utf-8')).hexdigest()
        },
        "error_detail": error_detail,
        "raw_response": raw_response_text
    }
    
    with open("aeg_proof_audit.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(proof_block, ensure_ascii=False) + "\n")
        
    return proof_block

async def call_anthropic_fallback(req_body: dict) -> Tuple[Optional[str], Optional[str]]:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return None, "ANTHROPIC_API_KEY_NOT_SET"

    messages = req_body.get("messages", [])
    anthropic_messages = []
    system_prompt = "Return strictly JSON matching schema: {\"user_id\": str, \"action\": str, \"amount\": float, \"confidence\": float}"
    
    for m in messages:
        if m.get("role") == "system":
            system_prompt += f"\n{m.get('content', '')}"
        elif m.get("role") in ["user", "assistant"]:
            anthropic_messages.append({"role": m.get("role"), "content": m.get("content")})

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": anthropic_messages
    }

    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            if res.status_code == 200:
                return res.text, None
            return None, f"Anthropic HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return None, f"Anthropic Exception: {str(e)}"

@app.post("/v1/chat/completions")
async def aegis_proxy(request: Request, authorization: Optional[str] = Header(None)):
    req_body = await request.json()
    api_key = authorization or f"Bearer {os.getenv('OPENAI_API_KEY', '')}"
    headers = {"Content-Type": "application/json", "Authorization": api_key}

    openai_res_text = ""
    is_silent_failure = False
    error_msg = ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            openai_res = await client.post(OPENAI_API_URL, json=req_body, headers=headers)
            res_status = openai_res.status_code
            openai_res_text = openai_res.text
            
            if res_status == 200:
                try:
                    res_json = json.loads(openai_res_text)
                    content_str = res_json["choices"][0]["message"]["content"]
                    extracted_data = json.loads(content_str)
                    ExpectedExtractionSchema.model_validate(extracted_data)
                    return Response(content=openai_res_text, status_code=200, media_type="application/json")
                except Exception as e:
                    is_silent_failure = True
                    error_msg = f"OpenAI Schema Error: {type(e).__name__} - {str(e)}"
            else:
                is_silent_failure = True
                error_msg = f"OpenAI HTTP Error: {res_status}"
        except Exception as e:
            is_silent_failure = True
            error_msg = f"OpenAI Network Error: {str(e)}"

    if is_silent_failure:
        proof = generate_proof_log(req_body, openai_res_text, error_msg)
        print(f"\n[AEG ALERT] OpenAI Failure Detected! Proof: {proof['hashes']['proof_signature']}")
        print("[AEG FALLBACK] Routing to Anthropic Claude...")

        claude_res_text, fallback_err = await call_anthropic_fallback(req_body)
        
        if claude_res_text:
            try:
                c_json = json.loads(claude_res_text)
                c_content = c_json["content"][0]["text"]
                c_extracted = json.loads(c_content)
                ExpectedExtractionSchema.model_validate(c_extracted)

                fallback_response = {
                    "aeg_status": "FALLBACK_SUCCESS_ANTHROPIC",
                    "proof_id": proof['hashes']['proof_signature'],
                    "openai_failure_reason": error_msg,
                    "fallback_provider": "anthropic-claude",
                    "data": c_extracted
                }
                return Response(content=json.dumps(fallback_response, ensure_ascii=False), status_code=200, media_type="application/json")
            except Exception as e:
                error_msg += f" | Claude Schema Error: {str(e)}"

        return Response(
            content=json.dumps({
                "aeg_status": "ALL_PROVIDERS_FAILED",
                "proof_id": proof['hashes']['proof_signature'],
                "error_detail": error_msg,
                "fallback_error": fallback_err
            }, ensure_ascii=False),
            status_code=502,
            media_type="application/json"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
