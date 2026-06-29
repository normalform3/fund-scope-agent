from typing import Dict, List, Optional, TypedDict

from app.models import FundProfile, NavPoint
from app.reports.generator import generate_fund_checkup_report
from app.services.fund_service import FundService


class FundCheckupState(TypedDict, total=False):
    code: str
    profile: FundProfile
    nav_points: List[NavPoint]
    report: Dict[str, object]
    errors: List[str]


class FundCheckupWorkflow:
    """Small LangGraph-compatible workflow wrapper.

    The deterministic implementation is kept as the source of truth. If
    LangGraph is installed, this class can be expanded into explicit graph
    nodes without changing the API contract.
    """

    def __init__(self, fund_service: Optional[FundService] = None) -> None:
        self.fund_service = fund_service or FundService()

    def run(self, code: str) -> Dict[str, object]:
        state: FundCheckupState = {"code": code, "errors": []}
        state = self._collect_data(state)
        if state.get("errors"):
            return {
                "conclusion": "数据不足，暂不评价",
                "summary": "基金数据获取失败，暂时无法生成体检报告。",
                "errors": state["errors"],
                "compliance_warnings": ["仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"],
            }
        state = self._generate_report(state)
        return state["report"]

    def _collect_data(self, state: FundCheckupState) -> FundCheckupState:
        try:
            code = state["code"]
            state["profile"] = self.fund_service.get_profile(code)
            state["nav_points"] = self.fund_service.get_nav_history(code)
        except Exception as exc:
            state.setdefault("errors", []).append(str(exc))
        return state

    def _generate_report(self, state: FundCheckupState) -> FundCheckupState:
        state["report"] = generate_fund_checkup_report(state["profile"], state["nav_points"])
        return state

