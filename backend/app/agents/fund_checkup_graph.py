from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, TypedDict

from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint
from app.reports.generator import generate_fund_checkup_report
from app.services.fund_service import FundService


class FundCheckupState(TypedDict, total=False):
    code: str
    risk_profile: Dict[str, object]
    profile: FundProfile
    nav_points: List[NavPoint]
    holdings: List[FundHolding]
    industry_allocation: List[IndustryAllocation]
    fees: List[FundFee]
    report: Dict[str, object]
    errors: List[str]
    data_warnings: List[str]
    workflow_trace: List[Dict[str, object]]
    data_events: List[Dict[str, object]]


class FundCheckupWorkflow:
    """Small LangGraph-compatible workflow wrapper.

    The deterministic implementation is kept as the source of truth. If
    LangGraph is installed, this class can be expanded into explicit graph
    nodes without changing the API contract.
    """

    def __init__(self, fund_service: Optional[FundService] = None) -> None:
        self.fund_service = fund_service or FundService()

    def run(self, code: str, risk_profile: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        state: FundCheckupState = {
            "code": code,
            "risk_profile": risk_profile or {},
            "errors": [],
            "workflow_trace": [],
            "data_events": [],
        }
        clear_events = getattr(self.fund_service, "clear_data_events", None)
        if callable(clear_events):
            clear_events()
        state = self._collect_data(state)
        get_events = getattr(self.fund_service, "get_data_events", None)
        if callable(get_events):
            state["data_events"] = get_events()
        if state.get("errors"):
            return _error_report(
                state["code"],
                state["errors"],
                state.get("risk_profile", {}),
                state.get("workflow_trace", []),
                state.get("data_events", []),
            )
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
        trace_by_name: Dict[str, Dict[str, object]] = {
            name: _trace_item(name, "pending", "等待采集")
            for name in jobs
        }
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            futures = {executor.submit(callable_, code): name for name, callable_ in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    state[name] = result
                    trace_by_name[name] = _trace_item(
                        name,
                        "success",
                        _success_message(name, result),
                        item_count=_item_count(result),
                    )
                except Exception as exc:
                    message = "%s: %s" % (name, exc)
                    if name in required:
                        state.setdefault("errors", []).append(message)
                        trace_by_name[name] = _trace_item(name, "error", str(exc))
                    else:
                        state.setdefault("data_warnings", []).append(message)
                        trace_by_name[name] = _trace_item(name, "degraded", str(exc), item_count=0)
                        state[name] = []
        state["workflow_trace"] = [trace_by_name[name] for name in jobs]
        return state

    def _generate_report(self, state: FundCheckupState) -> FundCheckupState:
        state["report"] = generate_fund_checkup_report(
            state["profile"],
            state["nav_points"],
            state.get("holdings", []),
            state.get("industry_allocation", []),
            state.get("fees", []),
            risk_profile=state.get("risk_profile", {}),
            workflow_trace=state.get("workflow_trace", []) + [_trace_item("report_generation", "success", "报告组装和合规检查完成")],
            data_warnings=state.get("data_warnings", []),
            data_events=state.get("data_events", []),
        )
        return state


def _error_report(
    code: str,
    errors: List[str],
    risk_profile: Optional[Dict[str, object]] = None,
    workflow_trace: Optional[List[Dict[str, object]]] = None,
    data_events: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    data_events = data_events or []
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
        "risk_explanation": [
            {
                "key": "data_unavailable",
                "title": "风险解释",
                "level": "数据不足",
                "metric_label": "数据源",
                "metric_value": None,
                "explanation": "基金核心数据获取失败，暂时无法解释亏损压力、波动体验和持有风险。",
                "user_meaning": "请稍后重试或切换数据源，当前结果不能作为风险判断依据。",
            }
        ],
        "risk_profile_assessment": {
            "status": "insufficient_data" if risk_profile else "not_provided",
            "fit_level": "数据不足" if risk_profile else "未评估",
            "profile": risk_profile or {},
            "reasons": ["基金核心数据获取失败，无法和用户风险画像做适配性判断。"] if risk_profile else ["未提供用户风险画像。"],
            "risk_flags": ["请在数据源恢复后重新生成报告。"] if risk_profile else ["可补充风险画像后再生成报告。"],
        },
        "risk_notes": ["数据源暂不可用，无法计算可靠风险指标。"],
        "holding_notes": ["数据源暂不可用，无法判断持仓和行业集中度。"],
        "suitable_for": ["希望稍后重试或更换数据源的用户"],
        "unsuitable_for": ["需要立即依据完整数据做判断的用户"],
        "data_notes": errors,
        "data_quality": [
            _quality_item("profile", "基金档案", "error", 0, _event_source(data_events, "profile", "unavailable"), "基金档案获取失败。"),
            _quality_item("nav_points", "历史净值", "error", 0, _event_source(data_events, "nav_points", "unavailable"), "历史净值获取失败，无法计算风险指标。"),
            _quality_item("risk_metrics", "风险指标", "insufficient", 0, "deterministic_metrics", "核心净值数据缺失，指标未计算。"),
            _quality_item("holdings", "持仓数据", "skipped", 0, _event_source(data_events, "holdings", "unavailable"), "核心数据失败，本次跳过持仓解释。"),
            _quality_item("industry_allocation", "行业配置", "skipped", 0, _event_source(data_events, "industry_allocation", "unavailable"), "核心数据失败，本次跳过行业配置解释。"),
            _quality_item("fees", "费率与交易规则", "skipped", 0, _event_source(data_events, "fees", "unavailable"), "核心数据失败，本次跳过费率解释。"),
        ],
        "workflow_trace": (workflow_trace or []) + [_trace_item("report_generation", "skipped", "核心数据失败，跳过报告组装")],
        "llm_commentary": "",
        "compliance_warnings": ["仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"],
        "errors": errors,
    }


def _trace_item(
    stage: str,
    status: str,
    message: str,
    item_count: Optional[int] = None,
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "stage": stage,
        "label": _stage_label(stage),
        "status": status,
        "message": message,
    }
    if item_count is not None:
        payload["item_count"] = item_count
    return payload


def _stage_label(stage: str) -> str:
    labels = {
        "profile": "基金档案",
        "nav_points": "历史净值",
        "holdings": "持仓数据",
        "industry_allocation": "行业配置",
        "fees": "费率与交易规则",
        "report_generation": "报告生成",
    }
    return labels.get(stage, stage)


def _success_message(name: str, result: object) -> str:
    if isinstance(result, list):
        return "已取得 %s 条%s。" % (len(result), _stage_label(name))
    return "已取得%s。" % _stage_label(name)


def _item_count(result: object) -> int:
    if isinstance(result, list):
        return len(result)
    return 1


def _quality_item(section: str, label: str, status: str, item_count: int, source: str, note: str) -> Dict[str, object]:
    return {
        "section": section,
        "label": label,
        "status": status,
        "item_count": item_count,
        "source": source,
        "note": note,
    }


def _event_source(data_events: List[Dict[str, object]], section: str, default: str) -> str:
    for event in data_events:
        if event.get("section") == section:
            return str(event.get("source") or default)
    return default
