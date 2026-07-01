from datetime import date
from typing import Dict, List, Optional

from app.compliance.checker import enforce_report_compliance
from app.metrics.calculator import calculate_risk_metrics
from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint, RiskMetrics


def generate_fund_checkup_report(
    profile: FundProfile,
    nav_points: List[NavPoint],
    holdings: List[FundHolding] = None,
    industry_allocation: List[IndustryAllocation] = None,
    fees: List[FundFee] = None,
    llm_commentary: str = "",
    risk_profile: Dict[str, object] = None,
    workflow_trace: List[Dict[str, object]] = None,
    data_warnings: List[str] = None,
    data_events: List[Dict[str, object]] = None,
) -> Dict[str, object]:
    holdings = holdings or []
    industry_allocation = industry_allocation or []
    fees = fees or []
    metrics = calculate_risk_metrics(nav_points)
    report = {
        "fund": profile.to_dict(),
        "conclusion": _classify_conclusion(metrics),
        "summary": _build_summary(profile, metrics),
        "metrics": metrics.to_dict(),
        "holdings": [item.to_dict() for item in holdings],
        "industry_allocation": [item.to_dict() for item in industry_allocation],
        "fees": [item.to_dict() for item in fees],
        "risk_explanation": _risk_explanation(metrics, holdings, industry_allocation),
        "risk_profile_assessment": _risk_profile_assessment(metrics, risk_profile or {}),
        "risk_notes": _risk_notes(metrics),
        "holding_notes": _holding_notes(holdings, industry_allocation),
        "suitable_for": _suitable_for(metrics),
        "unsuitable_for": _unsuitable_for(metrics),
        "data_notes": _data_notes(metrics, nav_points, holdings, industry_allocation, fees, risk_profile or {})
        + (data_warnings or []),
        "data_quality": _data_quality(
            profile,
            nav_points,
            holdings,
            industry_allocation,
            fees,
            metrics,
            workflow_trace or [],
            data_events or [],
        ),
        "workflow_trace": workflow_trace or [],
        "llm_commentary": llm_commentary,
        "compliance_warnings": [],
    }
    return enforce_report_compliance(report)


def _classify_conclusion(metrics: RiskMetrics) -> str:
    if metrics.total_return is None or metrics.observation_days < 120:
        return "数据不足，暂不评价"
    if metrics.max_drawdown is not None and metrics.max_drawdown <= -0.35:
        return "仅适合高风险用户"
    if metrics.annualized_volatility is not None and metrics.annualized_volatility > 0.32:
        return "仅适合高风险用户"
    if metrics.max_drawdown is not None and metrics.max_drawdown >= -0.12:
        return "适合长期观察"
    return "适合关注"


def _build_summary(profile: FundProfile, metrics: RiskMetrics) -> str:
    if metrics.total_return is None:
        return "%s 当前历史净值样本不足，暂时无法形成可靠体检结论。" % profile.name
    return (
        "%s 在当前样本区间内累计收益为 %s，最大回撤为 %s。"
        "该结论只反映历史数据中的风险收益特征，不代表未来表现。"
    ) % (
        profile.name,
        _format_percent(metrics.total_return),
        _format_percent(metrics.max_drawdown),
    )


def _risk_notes(metrics: RiskMetrics) -> List[str]:
    notes: List[str] = []
    if metrics.max_drawdown is None:
        notes.append("最大回撤无法计算，需补充更长历史净值。")
    elif metrics.max_drawdown <= -0.35:
        notes.append("历史最大回撤较深，净值波动可能超出普通稳健型用户承受范围。")
    elif metrics.max_drawdown <= -0.2:
        notes.append("历史最大回撤处于中高水平，需要关注回撤修复时间。")
    else:
        notes.append("历史最大回撤相对可控，但仍可能随市场环境扩大。")

    if metrics.annualized_volatility is None:
        notes.append("波动率无法计算，风险评价需谨慎。")
    elif metrics.annualized_volatility > 0.32:
        notes.append("年化波动率偏高，更接近权益或主题型基金风险特征。")
    elif metrics.annualized_volatility < 0.12:
        notes.append("年化波动率较低，历史波动相对平缓。")
    else:
        notes.append("年化波动率处于中等区间，仍需结合持仓和基金类型判断。")

    if metrics.sharpe_ratio is None:
        notes.append("夏普比率无法计算，可能是数据太短或波动率为零。")
    elif metrics.sharpe_ratio < 0:
        notes.append("夏普比率为负，样本期内风险调整后收益表现较弱。")
    elif metrics.sharpe_ratio < 0.5:
        notes.append("夏普比率不高，承担波动后获得的超额收益有限。")
    else:
        notes.append("夏普比率为正，样本期内风险调整后收益有一定解释力。")
    return notes


def _holding_notes(holdings: List[FundHolding], industry_allocation: List[IndustryAllocation]) -> List[str]:
    notes: List[str] = []
    if holdings:
        top_holding = holdings[0]
        notes.append(
            "最新可得持仓中，第一大持仓为 %s，占净值比例约 %s。"
            % (top_holding.stock_name, _format_percent_from_ratio(top_holding.ratio))
        )
        top_ten_ratio = sum(item.ratio or 0 for item in holdings[:10])
        if top_ten_ratio:
            notes.append("前十大持仓合计占净值比例约 %.2f%%，可用于观察集中度。" % top_ten_ratio)
    else:
        notes.append("暂未取得真实持仓数据，无法判断个股集中度。")

    if industry_allocation:
        top_industry = industry_allocation[0]
        notes.append(
            "最新可得行业配置中，第一大行业为 %s，占净值比例约 %s。"
            % (top_industry.industry, _format_percent_from_ratio(top_industry.ratio))
        )
    else:
        notes.append("暂未取得真实行业配置数据，无法判断行业集中度。")
    return notes


def _suitable_for(metrics: RiskMetrics) -> List[str]:
    if metrics.total_return is None:
        return ["希望先补齐历史数据后再判断的用户"]
    if metrics.max_drawdown is not None and metrics.max_drawdown <= -0.3:
        return ["能接受较大净值波动的高风险用户", "愿意长期跟踪基金风格和持仓变化的用户"]
    return ["希望把基金纳入观察池并持续比较的用户", "能接受净值阶段性波动的长期投资者"]


def _unsuitable_for(metrics: RiskMetrics) -> List[str]:
    items = ["需要短期确定性收益的用户", "无法接受本金波动的用户"]
    if metrics.max_drawdown is not None and metrics.max_drawdown <= -0.25:
        items.append("最大亏损承受能力较低的保守型用户")
    return items


def _data_notes(
    metrics: RiskMetrics,
    nav_points: List[NavPoint],
    holdings: List[FundHolding],
    industry_allocation: List[IndustryAllocation],
    fees: List[FundFee],
    risk_profile: Dict[str, object],
) -> List[str]:
    notes = list(metrics.warnings)
    if nav_points:
        notes.append("净值样本区间：%s 至 %s。" % (nav_points[0].date, nav_points[-1].date))
    notes.append("真实持仓条数：%s；真实行业配置条数：%s；费率/交易规则条数：%s。" % (len(holdings), len(industry_allocation), len(fees)))
    if risk_profile:
        notes.append("本次报告已按用户风险画像做确定性适配性解释，未使用 LLM 生成适配结论。")
    else:
        notes.append("本次报告未提供用户风险画像，适配性解释仅保留为通用风险提示。")
    notes.append("单基金报告尚未内嵌基金经理变更归因；同类参照可通过同类比较接口单独查看。")
    return notes


def _data_quality(
    profile: FundProfile,
    nav_points: List[NavPoint],
    holdings: List[FundHolding],
    industry_allocation: List[IndustryAllocation],
    fees: List[FundFee],
    metrics: RiskMetrics,
    workflow_trace: List[Dict[str, object]],
    data_events: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    source = profile.data_source or "unknown"
    events = _events_by_section(data_events)
    nav_note = "净值样本不足，无法可靠计算完整风险指标。"
    if nav_points:
        nav_note = "净值样本区间：%s 至 %s。" % (nav_points[0].date, nav_points[-1].date)
    metrics_note = "由历史净值确定性计算，未使用 LLM。"
    if metrics.total_return is None:
        metrics_note = "历史净值不足，部分指标无法计算。"
    return [
        _quality_item("profile", "基金档案", _quality_status(workflow_trace, events, "profile", bool(profile.code)), 1, _quality_source(events, "profile", source), _quality_note(events, "profile", "基金基础信息来自当前数据 provider。")),
        _quality_item("nav_points", "历史净值", _quality_status(workflow_trace, events, "nav_points", bool(nav_points)), len(nav_points), _quality_source(events, "nav_points", source), _quality_note(events, "nav_points", nav_note)),
        _quality_item("risk_metrics", "风险指标", "success" if metrics.total_return is not None else "insufficient", metrics.observation_days, "deterministic_metrics", metrics_note),
        _quality_item("holdings", "持仓数据", _quality_status(workflow_trace, events, "holdings", bool(holdings)), len(holdings), _quality_source(events, "holdings", source), _quality_note(events, "holdings", "用于判断个股集中度；为空时不推断持仓风险。")),
        _quality_item("industry_allocation", "行业配置", _quality_status(workflow_trace, events, "industry_allocation", bool(industry_allocation)), len(industry_allocation), _quality_source(events, "industry_allocation", source), _quality_note(events, "industry_allocation", "用于判断行业集中度；为空时不推断行业风险。")),
        _quality_item("fees", "费率与交易规则", _quality_status(workflow_trace, events, "fees", bool(fees)), len(fees), _quality_source(events, "fees", source), _quality_note(events, "fees", "用于展示申购、赎回或管理费等规则；为空时需后续补充。")),
    ]


def _quality_item(section: str, label: str, status: str, item_count: int, source: str, note: str) -> Dict[str, object]:
    return {
        "section": section,
        "label": label,
        "status": status,
        "item_count": item_count,
        "source": source,
        "note": note,
    }


def _trace_status(workflow_trace: List[Dict[str, object]], stage: str, has_data: bool) -> str:
    for item in workflow_trace:
        if item.get("stage") == stage:
            status = str(item.get("status", ""))
            if status in {"success", "degraded", "error", "skipped"}:
                return status
    return "success" if has_data else "missing"


def _events_by_section(data_events: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    events = {}
    for event in data_events:
        section = str(event.get("section") or "")
        if section:
            events[section] = event
    return events


def _quality_status(
    workflow_trace: List[Dict[str, object]],
    events: Dict[str, Dict[str, object]],
    section: str,
    has_data: bool,
) -> str:
    event = events.get(section, {})
    if event.get("fallback"):
        return "fallback"
    if event.get("cache_hit"):
        return "cached"
    return _trace_status(workflow_trace, section, has_data)


def _quality_source(events: Dict[str, Dict[str, object]], section: str, default: str) -> str:
    event = events.get(section, {})
    return str(event.get("source") or default)


def _quality_note(events: Dict[str, Dict[str, object]], section: str, default: str) -> str:
    event = events.get(section, {})
    message = str(event.get("message") or "").strip()
    if message:
        return message
    if event.get("cache_hit"):
        return "命中本地缓存；请结合缓存 TTL 判断实时性。"
    return default


def _risk_profile_assessment(metrics: RiskMetrics, risk_profile: Dict[str, object]) -> Dict[str, object]:
    normalized = _normalize_risk_profile(risk_profile)
    if not risk_profile:
        return {
            "status": "not_provided",
            "fit_level": "未评估",
            "profile": normalized,
            "reasons": ["未提供用户风险画像，暂不判断该基金与个人承受能力的适配性。"],
            "risk_flags": ["可补充风险偏好、最长持有期限、流动性需求和最大可承受阶段性亏损。"],
        }
    if metrics.max_drawdown is None or metrics.annualized_volatility is None:
        return {
            "status": "insufficient_data",
            "fit_level": "数据不足",
            "profile": normalized,
            "reasons": ["基金风险指标不完整，暂时无法和用户风险画像做可靠匹配。"],
            "risk_flags": ["需要补充更长净值历史后再判断适配性。"],
        }

    reasons = [
        "用户风险偏好：%s；资金期限：%s；流动性需求：%s。"
        % (
            _risk_tolerance_label(normalized["risk_tolerance"]),
            _horizon_label(normalized["horizon"]),
            _liquidity_label(normalized["liquidity_need"]),
        )
    ]
    risk_flags: List[str] = []
    score = 0

    max_loss_tolerance = normalized["max_loss_tolerance"]
    if isinstance(max_loss_tolerance, (float, int)):
        reasons.append(
            "用户可承受阶段性亏损约 %s；该基金样本期最大回撤为 %s。"
            % (_format_percent(max_loss_tolerance), _format_percent(metrics.max_drawdown))
        )
        if abs(metrics.max_drawdown) > max_loss_tolerance:
            score += 2
            risk_flags.append("基金历史最大回撤超过用户填写的可承受阶段性亏损。")

    investment_horizon_months = normalized["investment_horizon_months"]
    if isinstance(investment_horizon_months, int):
        horizon_trading_days = investment_horizon_months * 21
        reasons.append(
            "用户预计持有约 %s 个月，可近似观察 %s 个交易日内的回撤修复压力。"
            % (investment_horizon_months, horizon_trading_days)
        )
        if metrics.drawdown_recovery_days is None and metrics.max_drawdown < -0.05:
            score += 1
            risk_flags.append("样本期最大回撤尚未修复，无法确认是否适配用户预计持有期限。")
        elif isinstance(metrics.drawdown_recovery_days, int) and metrics.drawdown_recovery_days > horizon_trading_days:
            score += 1
            risk_flags.append("历史最大回撤修复时间超过用户预计持有期限。")

    can_delay_use = normalized["can_delay_use"]
    if isinstance(can_delay_use, bool):
        reasons.append("到期用钱是否可延期：%s。" % ("可以延期" if can_delay_use else "不方便延期"))
        if not can_delay_use and metrics.max_drawdown < -0.05:
            if metrics.drawdown_recovery_days is None:
                score += 1
                risk_flags.append("这笔钱不方便延期使用，而样本期最大回撤尚未修复。")
            elif isinstance(investment_horizon_months, int) and metrics.drawdown_recovery_days > investment_horizon_months * 21:
                score += 1
                risk_flags.append("这笔钱不方便延期使用，而历史回撤修复时间超过预计持有期限。")
            elif metrics.annualized_volatility > 0.12:
                score += 1
                risk_flags.append("这笔钱不方便延期使用，较明显净值波动可能增加到期用钱压力。")

    money_purpose = normalized["money_purpose"]
    if money_purpose:
        reasons.append("资金用途：%s。" % _money_purpose_label(money_purpose))
        if money_purpose in {"emergency", "education", "near_term"}:
            if metrics.drawdown_recovery_days is None and metrics.max_drawdown < -0.05:
                score += 1
                risk_flags.append("资金用途偏刚性，遇到未修复回撤时可能影响到期用钱。")
            elif metrics.annualized_volatility > 0.12:
                score += 1
                risk_flags.append("资金用途偏刚性，较明显净值波动可能增加使用前的不确定性。")

    limits = {
        "low": {"max_drawdown": -0.12, "max_volatility": 0.12},
        "medium": {"max_drawdown": -0.25, "max_volatility": 0.22},
        "high": {"max_drawdown": -0.4, "max_volatility": 0.36},
    }
    limit = limits.get(normalized["risk_tolerance"], limits["medium"])
    if metrics.max_drawdown < limit["max_drawdown"]:
        score += 1
        risk_flags.append("最大回撤超过当前风险偏好的参考边界。")
    if metrics.annualized_volatility > limit["max_volatility"]:
        score += 1
        risk_flags.append("年化波动率超过当前风险偏好的参考边界。")
    if normalized["horizon"] == "short" and metrics.drawdown_recovery_days is None and metrics.max_drawdown < -0.05:
        score += 1
        risk_flags.append("资金期限偏短，而样本期回撤尚未完全修复。")
    if normalized["liquidity_need"] == "high" and metrics.annualized_volatility > 0.12:
        score += 1
        risk_flags.append("流动性需求较高时，较明显净值波动可能影响用钱计划。")

    if not risk_flags:
        fit_level = "可观察"
        reasons.append("当前历史风险指标未明显突破用户画像的参考边界。")
    elif score >= 3:
        fit_level = "不匹配"
    else:
        fit_level = "需要谨慎"

    return {
        "status": "assessed",
        "fit_level": fit_level,
        "profile": normalized,
        "reasons": reasons,
        "risk_flags": risk_flags or ["仍需结合持仓、费用、基金经理变化和同类比较继续观察。"],
    }


def _normalize_risk_profile(risk_profile: Dict[str, object]) -> Dict[str, object]:
    return {
        "risk_tolerance": _normalize_choice(risk_profile.get("risk_tolerance"), {"low", "medium", "high"}, "medium"),
        "horizon": _normalize_choice(risk_profile.get("horizon"), {"short", "medium", "long"}, "medium"),
        "liquidity_need": _normalize_choice(risk_profile.get("liquidity_need"), {"high", "medium", "low"}, "medium"),
        "max_loss_tolerance": _normalize_loss_tolerance(risk_profile.get("max_loss_tolerance")),
        "investment_horizon_months": _normalize_positive_int(risk_profile.get("investment_horizon_months")),
        "can_delay_use": _normalize_optional_bool(risk_profile.get("can_delay_use")),
        "money_purpose": _normalize_money_purpose(risk_profile.get("money_purpose")),
    }


def _normalize_choice(value: object, allowed: set, default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else default


def _normalize_loss_tolerance(value: object) -> object:
    if value is None:
        return None
    try:
        number = abs(float(value))
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return min(number, 1.0)


def _normalize_positive_int(value: object) -> object:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalize_optional_bool(value: object) -> object:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "1", "y", "可以", "可延期", "能延期", "能", "是"}:
        return True
    if text in {"false", "no", "0", "n", "不可以", "不可延期", "不能延期", "不能", "否"}:
        return False
    return None


def _normalize_money_purpose(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    mapping = {
        "emergency": "emergency",
        "备用金": "emergency",
        "应急": "emergency",
        "生活费": "emergency",
        "education": "education",
        "教育": "education",
        "学费": "education",
        "retirement": "retirement",
        "养老": "retirement",
        "退休": "retirement",
        "idle": "idle",
        "闲置": "idle",
        "观察": "idle",
        "near_term": "near_term",
        "近期": "near_term",
        "买房": "near_term",
        "购房": "near_term",
        "首付": "near_term",
        "旅行": "near_term",
    }
    raw = str(value)
    for source, target in mapping.items():
        if text == source or source in raw:
            return target
    return text if text in {"emergency", "education", "retirement", "idle", "near_term"} else ""


def _money_purpose_label(value: str) -> str:
    return {
        "emergency": "应急备用金",
        "education": "教育支出",
        "retirement": "养老长期资金",
        "idle": "闲置观察资金",
        "near_term": "近期目标资金",
    }.get(value, value)


def _risk_explanation(
    metrics: RiskMetrics,
    holdings: List[FundHolding],
    industry_allocation: List[IndustryAllocation],
) -> List[Dict[str, object]]:
    return [
        _loss_pressure_explanation(metrics),
        _drawdown_journey_explanation(metrics),
        _volatility_experience_explanation(metrics),
        _exposure_concentration_explanation(holdings, industry_allocation),
        _holding_risk_explanation(metrics),
        _risk_adjusted_return_explanation(metrics),
    ]


def _loss_pressure_explanation(metrics: RiskMetrics) -> Dict[str, object]:
    value = metrics.max_drawdown
    if value is None:
        return _explanation_item(
            "loss_pressure",
            "亏损压力",
            "数据不足",
            "最大回撤",
            value,
            "最大回撤无法计算，暂时不能判断历史上最深的净值下跌幅度。",
            "需要补充更长净值历史后，再评估持有中可能遇到的阶段性亏损压力。",
        )
    if value <= -0.35:
        level = "高"
        meaning = "如果在阶段高点买入，历史上曾经历很深的净值回落，持有者需要较强的亏损承受能力。"
    elif value <= -0.2:
        level = "中高"
        meaning = "历史上出现过明显回撤，短期资金或保守型用户可能会感到压力较大。"
    elif value <= -0.1:
        level = "中"
        meaning = "历史回撤不算轻微，持有过程中仍可能出现需要耐心等待修复的阶段。"
    else:
        level = "较低"
        meaning = "样本期内最大回撤相对较浅，但历史表现不能排除未来更大波动。"
    return _explanation_item(
        "loss_pressure",
        "亏损压力",
        level,
        "最大回撤",
        value,
        "样本期最大回撤为 %s，表示从阶段高点到低点的最大净值下跌幅度。"
        % _format_percent(value),
        meaning,
    )


def _drawdown_journey_explanation(metrics: RiskMetrics) -> Dict[str, object]:
    value = metrics.max_drawdown
    start = metrics.max_drawdown_start
    trough = metrics.max_drawdown_trough
    if value is None or not start or not trough:
        return _explanation_item(
            "drawdown_journey",
            "最难熬区间",
            "数据不足",
            "最大回撤",
            value,
            "最大回撤区间无法识别，暂时不能还原历史上最难熬的一段下跌过程。",
            "需要更完整的连续净值，才能判断下跌从何时开始、何时到达低点以及是否修复。",
        )

    drawdown_days = _calendar_days_between(start, trough)
    if drawdown_days is None:
        explanation = "样本期最大回撤发生在 %s 至 %s 之间，回撤幅度为 %s。" % (
            start,
            trough,
            _format_percent(value),
        )
    else:
        explanation = "样本期最大回撤从 %s 到 %s，约 %s 个自然日内下跌 %s。" % (
            start,
            trough,
            drawdown_days,
            _format_percent(value),
        )

    if metrics.drawdown_recovery_days is None:
        level = "高" if value <= -0.2 else "中"
        meaning = "样本期末尚未识别到回到此前高点，用户需要把这类未修复回撤视为真实持有压力。"
    elif metrics.drawdown_recovery_days > 252:
        level = "中高"
        meaning = "这段下跌之后修复超过一年交易日，说明等待净值回到前高可能需要较长耐心。"
    elif metrics.drawdown_recovery_days > 63:
        level = "中"
        meaning = "这段下跌之后修复用了数月，短期资金遇到类似阶段时可能会比较被动。"
    else:
        level = "较低"
        meaning = "这段下跌之后修复较快，但历史修复速度不能外推为未来也会快速修复。"

    return _explanation_item(
        "drawdown_journey",
        "最难熬区间",
        level,
        "最大回撤",
        value,
        explanation,
        meaning,
    )


def _volatility_experience_explanation(metrics: RiskMetrics) -> Dict[str, object]:
    value = metrics.annualized_volatility
    if value is None:
        return _explanation_item(
            "volatility_experience",
            "波动体验",
            "数据不足",
            "年化波动率",
            value,
            "年化波动率无法计算，暂时不能判断日常净值起伏强度。",
            "需要更多连续净值数据，才能评估持有过程是否平稳。",
        )
    if value > 0.32:
        level = "高"
        meaning = "净值起伏可能比较剧烈，用户需要能接受较频繁、较明显的账面波动。"
    elif value >= 0.18:
        level = "中高"
        meaning = "净值波动感会比较明显，适合愿意持续观察并接受阶段性起伏的用户。"
    elif value >= 0.08:
        level = "中"
        meaning = "净值有一定起伏，但不属于样本中的高波动区间。"
    else:
        level = "较低"
        meaning = "样本期净值起伏相对平缓，但仍需结合资产类别和市场环境判断。"
    return _explanation_item(
        "volatility_experience",
        "波动体验",
        level,
        "年化波动率",
        value,
        "年化波动率为 %s，可近似理解为持有过程中的净值起伏强度。"
        % _format_percent(value),
        meaning,
    )


def _exposure_concentration_explanation(
    holdings: List[FundHolding],
    industry_allocation: List[IndustryAllocation],
) -> Dict[str, object]:
    valid_holding_ratios = [item.ratio for item in holdings[:10] if isinstance(item.ratio, (float, int))]
    top_ten_ratio = sum(valid_holding_ratios) if valid_holding_ratios else None
    top_holding = next((item for item in holdings if isinstance(item.ratio, (float, int))), None)
    top_industry = next((item for item in industry_allocation if isinstance(item.ratio, (float, int))), None)

    if top_ten_ratio is None and top_industry is None:
        return _explanation_item(
            "exposure_concentration",
            "持仓集中度",
            "数据不足",
            "持仓占比",
            None,
            "暂未取得可用的持仓或行业配置比例，无法判断基金是否集中在少数股票或行业。",
            "需要补充最新持仓和行业配置后，再观察组合是否过度依赖少数资产。",
        )

    top_ten_text = _format_percent_from_ratio(top_ten_ratio) if top_ten_ratio is not None else "无法计算"
    top_holding_text = (
        "%s 占净值约 %s" % (top_holding.stock_name, _format_percent_from_ratio(top_holding.ratio))
        if top_holding
        else "第一大持仓无法计算"
    )
    top_industry_text = (
        "%s 占净值约 %s" % (top_industry.industry, _format_percent_from_ratio(top_industry.ratio))
        if top_industry
        else "第一大行业无法计算"
    )

    top_holding_ratio = top_holding.ratio if top_holding else 0
    top_industry_ratio = top_industry.ratio if top_industry else 0
    if (top_ten_ratio or 0) >= 55 or top_industry_ratio >= 45 or top_holding_ratio >= 12:
        level = "高"
        meaning = "组合较依赖少数股票或行业，相关资产一旦波动，基金净值可能受到更集中影响。"
    elif (top_ten_ratio or 0) >= 35 or top_industry_ratio >= 30 or top_holding_ratio >= 8:
        level = "中"
        meaning = "组合存在一定集中度，需要结合基金类型和历史调仓继续观察。"
    else:
        level = "较低"
        meaning = "当前披露口径下集中度相对分散，但持仓披露有滞后，仍需后续跟踪更新。"

    explanation = "最新可得披露中，前十大持仓合计约 %s；%s；第一大行业为 %s。" % (
        top_ten_text,
        top_holding_text,
        top_industry_text,
    )
    return _explanation_item(
        "exposure_concentration",
        "持仓集中度",
        level,
        "前十大持仓占比",
        _ratio_percent_to_decimal(top_ten_ratio),
        explanation,
        meaning,
    )


def _holding_risk_explanation(metrics: RiskMetrics) -> Dict[str, object]:
    if metrics.max_drawdown is None:
        return _explanation_item(
            "holding_risk",
            "持有风险",
            "数据不足",
            "回撤修复",
            None,
            "回撤区间无法识别，暂时不能判断历史修复时间。",
            "需要更完整的净值序列，才能判断遇到下跌后可能需要多长观察周期。",
        )
    if metrics.max_drawdown == 0:
        return _explanation_item(
            "holding_risk",
            "持有风险",
            "较低",
            "回撤修复",
            metrics.drawdown_recovery_days,
            "样本期未识别到明显回撤。",
            "当前样本看不出较大修复压力，但样本外风险仍需保留余地。",
        )
    if metrics.drawdown_recovery_days is None:
        level = "高" if metrics.max_drawdown <= -0.2 else "中"
        explanation = "样本期最大回撤后尚未回到此前高点。"
        meaning = "如果资金期限较短，可能来不及等待净值修复；更适合作为持续观察对象。"
    elif metrics.drawdown_recovery_days > 252:
        level = "中高"
        explanation = "样本期最大回撤修复用时约 %s 个交易日。" % metrics.drawdown_recovery_days
        meaning = "历史修复周期较长，持有者需要准备跨年度观察的耐心。"
    elif metrics.drawdown_recovery_days > 63:
        level = "中"
        explanation = "样本期最大回撤修复用时约 %s 个交易日。" % metrics.drawdown_recovery_days
        meaning = "回撤修复可能需要数月，不适合完全依赖短期流动性的资金。"
    else:
        level = "较低"
        explanation = "样本期最大回撤修复用时约 %s 个交易日。" % metrics.drawdown_recovery_days
        meaning = "历史修复速度相对较快，但不能代表未来下跌也会快速修复。"
    return _explanation_item(
        "holding_risk",
        "持有风险",
        level,
        "回撤修复",
        metrics.drawdown_recovery_days,
        explanation,
        meaning,
    )


def _risk_adjusted_return_explanation(metrics: RiskMetrics) -> Dict[str, object]:
    value = metrics.sharpe_ratio
    if value is None:
        return _explanation_item(
            "risk_adjusted_return",
            "风险收益匹配",
            "数据不足",
            "夏普比率",
            value,
            "夏普比率无法计算，可能是数据太短或波动率为零。",
            "暂时不能判断承担波动后获得的收益补偿是否充分。",
        )
    if value < 0:
        level = "偏弱"
        meaning = "样本期承担波动后没有获得正向补偿，需要谨慎解读收益表现。"
    elif value < 0.5:
        level = "一般"
        meaning = "风险调整后收益补偿有限，不能只看累计收益。"
    elif value < 1:
        level = "尚可"
        meaning = "风险调整后收益有一定解释力，但仍需结合同类比较和持仓变化。"
    else:
        level = "较好"
        meaning = "样本期风险调整后表现较强，但不代表未来能延续。"
    return _explanation_item(
        "risk_adjusted_return",
        "风险收益匹配",
        level,
        "夏普比率",
        value,
        "夏普比率为 %s，用于观察承担波动后获得的收益补偿。"
        % _format_number(value),
        meaning,
    )


def _explanation_item(
    key: str,
    title: str,
    level: str,
    metric_label: str,
    metric_value: object,
    explanation: str,
    user_meaning: str,
) -> Dict[str, object]:
    return {
        "key": key,
        "title": title,
        "level": level,
        "metric_label": metric_label,
        "metric_value": metric_value,
        "explanation": explanation,
        "user_meaning": user_meaning,
    }


def _format_percent(value: object) -> str:
    if not isinstance(value, (float, int)):
        return "无法计算"
    return "%.2f%%" % (value * 100)


def _format_percent_from_ratio(value: object) -> str:
    if not isinstance(value, (float, int)):
        return "无法计算"
    return "%.2f%%" % value


def _format_number(value: object) -> str:
    if not isinstance(value, (float, int)):
        return "无法计算"
    return "%.2f" % value


def _ratio_percent_to_decimal(value: object) -> object:
    if not isinstance(value, (float, int)):
        return None
    return round(value / 100, 6)


def _calendar_days_between(start: str, end: str) -> Optional[int]:
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except (TypeError, ValueError):
        return None
    return max((end_date - start_date).days, 0)


def _risk_tolerance_label(value: str) -> str:
    return {"low": "保守", "medium": "平衡", "high": "进取"}.get(value, "平衡")


def _horizon_label(value: str) -> str:
    return {"short": "短期", "medium": "中期", "long": "长期"}.get(value, "中期")


def _liquidity_label(value: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value, "中")
