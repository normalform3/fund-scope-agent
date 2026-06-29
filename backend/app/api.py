from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents.fund_checkup_graph import FundCheckupWorkflow
from app.services.fund_service import FundService

app = FastAPI(title="FundScope Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fund_service = FundService()
workflow = FundCheckupWorkflow(fund_service=fund_service)


class FundCheckupRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Fund code")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "fundscope-agent"}


@app.get("/api/funds/search")
def search_funds(q: str = "") -> Dict[str, object]:
    funds = fund_service.search_funds(q)
    return {"items": [fund.to_dict() for fund in funds]}


@app.get("/api/funds/{code}/profile")
def get_profile(code: str) -> Dict[str, object]:
    try:
        return fund_service.get_profile(code).to_dict()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/funds/{code}/nav")
def get_nav(code: str) -> Dict[str, object]:
    try:
        points = fund_service.get_nav_history(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"items": [point.to_dict() for point in points]}


@app.post("/api/reports/fund-checkup")
def create_fund_checkup(request: FundCheckupRequest) -> Dict[str, object]:
    return workflow.run(request.code.strip())

