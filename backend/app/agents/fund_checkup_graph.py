from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, TypedDict

from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint
from app.reports.generator import generate_fund_checkup_report
from app.services.fund_service import FundService


class FundCheckupState(TypedDict, total=False):
    code: str
    profile: FundProfile
    nav_points: List[NavPoint]
    holdings: List[FundHolding]
    industry_allocation: List[IndustryAllocation]
    fees: List[FundFee]
    report: Dict[str, object]
    errors: List[str]
    data_warnings: List[str]


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
            return _error_report(state["code"], state["errors"])
        state = self._generate_report(state)
        return state["report"]

    def _collect_data(self, state: FundCheckupState) -> FundCheckupState:
        code = state["code"]
        jobs = {
            "profile": self.fund_service.get_profile,
            "nav_points": self.fund_service.get_nav_history,
            "holdings": self.fund_service.get_holdings,
            "industry_allocation": self.fund_service.get_industry_allocation,
            "fees": self.fund_service.get_fees,
        }
        required = {"profile", "nav_points"}
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            futures = {executor.submit(callable_, code): name for name, callable_ in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    state[name] = future.result()
                except Exception as exc:
                    if name in required:
                        state.setdefault("errors", []).append("%s: %s" % (name, exc))
                    else:
                        state.setdefault("data_warnings", []).append("%s: %s" % (name, exc))
                        state[name] = []
        return state

    def _generate_report(self, state: FundCheckupState) -> FundCheckupState:
        state["report"] = generate_fund_checkup_report(
            state["profile"],
            state["nav_points"],
            state.get("holdings", []),
            state.get("industry_allocation", []),
            state.get("fees", []),
        )
        return state


def _error_report(code: str, errors: List[str]) -> Dict[str, object]:
    return {
        "fund": {
            "code": code,
            "name": code,
            "fund_type": "未知",
            "inception_date": "待补充",
            "manager": "待补充",
            "company": "待补充",
            "scale": "待补充",
            "purchase_status": "待确认",
            "redeem_status": "待确认",
            "fee_note": "待补充",
            "benchmark": "待补充",
            "investment_objective": "",
            "investment_strategy": "",
            "custodian": "",
            "rating": "",
            "data_source": "unavailable",
        },
        "conclusion": "数据不足，暂不评价",
        "summary": "基金数据获取失败，暂时无法生成体检报告。",
        "metrics": {
            "observation_days": 0,
            "total_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
            "calmar_ratio": None,
            "win_rate": None,
            "max_drawdown_start": None,
            "max_drawdown_trough": None,
            "drawdown_recovery_days": None,
            "period_returns": {"1m": None, "3m": None, "6m": None, "1y": None, "3y": None},
            "drawdown_series": [],
            "warnings": errors,
        },
        "holdings": [],
        "industry_allocation": [],
        "fees": [],
        "risk_notes": ["数据源暂不可用，无法计算可靠风险指标。"],
        "holding_notes": ["数据源暂不可用，无法判断持仓和行业集中度。"],
        "suitable_for": ["希望稍后重试或更换数据源的用户"],
        "unsuitable_for": ["需要立即依据完整数据做判断的用户"],
        "data_notes": errors,
        "llm_commentary": "",
        "compliance_warnings": ["仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"],
        "errors": errors,
    }
