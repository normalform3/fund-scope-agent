from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents.fund_discovery import FundDiscoveryWorkflow
from app.agents.fund_checkup_graph import FundCheckupWorkflow
from app.services.fund_service import FundService
from app.services.llm_service import LLMService

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
discovery_workflow = FundDiscoveryWorkflow(fund_service=fund_service)
llm_service = LLMService()


class FundCheckupRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Fund code")


class FundDiscoveryRequest(BaseModel):
    goal_text: str = Field("", description="Natural-language investment goal")
    answers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Structured questionnaire answers: horizon, risk_tolerance, liquidity_need, experience_level, investment_goal",
    )
    include_candidates: bool = Field(False, description="Whether to refine fund type matches into fund candidates")
    selected_fund_type: str = Field("", description="Fund type selected by the user for candidate refinement")
    refinement_text: str = Field("", description="Additional refinement requirements")


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
    except Exception as exc:
        raise HTTPException(status_code=502, detail="净值数据获取失败：%s" % str(exc))
    return {"items": [point.to_dict() for point in points]}


@app.get("/api/funds/{code}/holdings")
def get_holdings(code: str) -> Dict[str, object]:
    return {"items": [item.to_dict() for item in fund_service.get_holdings(code)]}


@app.get("/api/funds/{code}/industry-allocation")
def get_industry_allocation(code: str) -> Dict[str, object]:
    return {"items": [item.to_dict() for item in fund_service.get_industry_allocation(code)]}


@app.get("/api/funds/{code}/fees")
def get_fees(code: str) -> Dict[str, object]:
    return {"items": [item.to_dict() for item in fund_service.get_fees(code)]}


@app.post("/api/reports/fund-checkup")
def create_fund_checkup(request: FundCheckupRequest) -> Dict[str, object]:
    return workflow.run(request.code.strip())


@app.post("/api/fund-discovery")
def create_fund_discovery(request: FundDiscoveryRequest) -> Dict[str, object]:
    return discovery_workflow.run(
        request.goal_text.strip(),
        request.answers or {},
        include_candidates=request.include_candidates,
        selected_fund_type=request.selected_fund_type.strip(),
        refinement_text=request.refinement_text.strip(),
    )


@app.get("/api/llm/health")
def llm_health() -> Dict[str, object]:
    return llm_service.test_connection()
