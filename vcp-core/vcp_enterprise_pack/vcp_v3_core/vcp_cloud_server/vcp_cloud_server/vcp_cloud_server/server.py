from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import time
from typing import List, Optional

app = FastAPI(title="VCP Enterprise Cloud Control Plane", version="3.0.0")

# モックデータベース（本来は PostgreSQL / DynamoDB）
API_KEYS_DB = {
    "vcp_live_tier_enterprise_999": {"tenant_id": "tenant_acme_corp", "plan": "enterprise", "monthly_quota": 1000000},
    "vcp_live_tier_pro_123": {"tenant_id": "tenant_startup_inc", "plan": "pro", "monthly_quota": 50000}
}

TENANT_USAGE_DB = {}

# データモデル
class TelemetryEntry(BaseModel):
    token_id: str
    action: str
    resource: str
    amount: float
    status: str
    proof_hash: str
    timestamp: float

class IngestPayload(BaseModel):
    events: List[TelemetryEntry]

# APIキー認証ミドルウェア
def authenticate_tenant(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key not in API_KEYS_DB:
        raise HTTPException(status_code=401, detail="無効なVCP APIキーです。")
    return API_KEYS_DB[x_api_key]

@app.get("/")
def health_check():
    return {"status": "online", "system": "VCP Control Plane v3.0"}

# ポリシー配信エンドポイント（リモート動的変更用）
@app.get("/v1/policy/sync")
def sync_policy(tenant: dict = Depends(authenticate_tenant)):
    return {
        "tenant_id": tenant["tenant_id"],
        "policy": {
            "target_resource": "aws_ec2",
            "max_budget_per_action": 100000.0 if tenant["plan"] == "enterprise" else 20000.0,
            "allowed_actions": ["create_instance", "stop_instance"]
        }
    }

# ログ一元収集 ＆ 従量課金メトリクス収集エンドポイント
@app.post("/v1/telemetry/ingest")
def ingest_telemetry(payload: IngestPayload, tenant: dict = Depends(authenticate_tenant)):
    tenant_id = tenant["tenant_id"]
    current_count = TENANT_USAGE_DB.get(tenant_id, 0)
    
    # イベント件数をカウントアップ（Stripe従量課金メタデータ用）
    new_count = current_count + len(payload.events)
    TENANT_USAGE_DB[tenant_id] = new_count

    print(f"  └─ ☁️ [Cloud Ingest] {tenant_id} から {len(payload.events)} 件の暗号証跡を受信 | 累計請求カウント: {new_count} リクエスト")
    
    return {
        "status": "success",
        "processed": len(payload.events),
        "total_billable_requests": new_count
    }

# 企業向けダッシュボード用メトリクス取得
@app.get("/v1/dashboard/usage")
def get_usage(tenant: dict = Depends(authenticate_tenant)):
    tenant_id = tenant["tenant_id"]
    return {
        "tenant_id": tenant_id,
        "plan": tenant["plan"],
        "total_requests": TENANT_USAGE_DB.get(tenant_id, 0),
        "quota": tenant["monthly_quota"]
    }
