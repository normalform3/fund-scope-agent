from typing import Dict, List

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
        "risk_notes": _risk_notes(metrics),
        "holding_notes": _holding_notes(holdings, industry_allocation),
        "suitable_for": _suitable_for(metrics),
        "unsuitable_for": _unsuitable_for(metrics),
        "data_notes": _data_notes(metrics, nav_points, holdings, industry_allocation, fees),
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
) -> List[str]:
    notes = list(metrics.warnings)
    if nav_points:
        notes.append("净值样本区间：%s 至 %s。" % (nav_points[0].date, nav_points[-1].date))
    notes.append("真实持仓条数：%s；真实行业配置条数：%s；费率/交易规则条数：%s。" % (len(holdings), len(industry_allocation), len(fees)))
    notes.append("V1 尚未接入基金经理变更归因、同类排名和用户风险画像，相关判断将在后续版本增强。")
    return notes


def _format_percent(value: object) -> str:
    if not isinstance(value, (float, int)):
        return "无法计算"
    return "%.2f%%" % (value * 100)


def _format_percent_from_ratio(value: object) -> str:
    if not isinstance(value, (float, int)):
        return "无法计算"
    return "%.2f%%" % value
