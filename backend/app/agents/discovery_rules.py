from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from app.models import FundTypeMatch, InvestorPreferenceProfile


RISK_LIMITS = {
    "low": {"max_volatility": 0.12, "max_drawdown": -0.12},
    "medium": {"max_volatility": 0.24, "max_drawdown": -0.25},
    "high": {"max_volatility": 0.45, "max_drawdown": -0.45},
}

MIN_OBSERVATION_DAYS = 120
MAX_CANDIDATE_PROFILES = 36
MAX_SEARCH_TERMS = 12
MAX_CODE_TABLE_FUNDS = 120


@dataclass(frozen=True)
class FundTypeRule:
    fund_type: str
    reason: str
    unsuitable_for: str
    search_keywords: List[str]
    name_keywords: List[str]
    seed_codes: List[str]

    def to_match(self, profile: Optional[InvestorPreferenceProfile] = None, rank: int = 0) -> FundTypeMatch:
        return FundTypeMatch(
            fund_type=self.fund_type,
            reason=self.reason,
            unsuitable_for=self.unsuitable_for,
            search_keywords=self.search_keywords,
            fit_score=_fit_score(self, profile, rank),
            basis=_basis(self, profile),
            risk_flags=_risk_flags(self, profile),
            missing_context=_missing_context(profile),
        )


FUND_TYPE_RULES: Dict[str, FundTypeRule] = {
    "money_short_bond": FundTypeRule(
        fund_type="货币型 / 短债型",
        reason="更重视流动性和低波动，适合作为短期资金的研究起点。",
        unsuitable_for="不适合追求较高长期收益弹性的用户。",
        search_keywords=["货币", "短债", "同业存单", "债券"],
        name_keywords=["货币", "现金", "短债", "同业存单"],
        seed_codes=["000198"],
    ),
    "bond": FundTypeRule(
        fund_type="债券型",
        reason="当前画像更关注回撤控制，债券型基金通常比权益类基金波动更低。",
        unsuitable_for="不适合希望主要获取权益市场上涨弹性的用户。",
        search_keywords=["债券", "纯债", "短债", "中短债", "国开债"],
        name_keywords=["债", "纯债", "短债", "国开债", "政金债"],
        seed_codes=["003376"],
    ),
    "bond_plus": FundTypeRule(
        fund_type="债券型 / 固收+",
        reason="在控制回撤的同时保留一定收益弹性，适合作为平衡型研究方向。",
        unsuitable_for="不适合完全不能接受净值波动的用户。",
        search_keywords=["债券", "固收", "二级债", "偏债"],
        name_keywords=["债", "固收", "二级债", "偏债"],
        seed_codes=["003376"],
    ),
    "broad_index": FundTypeRule(
        fund_type="宽基指数型",
        reason="适合用透明、分散的权益敞口观察长期市场表现。",
        unsuitable_for="不适合短期资金或无法接受阶段性回撤的用户。",
        search_keywords=["沪深300", "中证500", "指数", "创业板"],
        name_keywords=["指数", "沪深300", "中证", "上证", "创业板", "ETF联接"],
        seed_codes=["110020"],
    ),
    "equity_hybrid": FundTypeRule(
        fund_type="偏股混合型",
        reason="适合愿意承担较大波动、关注主动管理能力的用户进一步体检。",
        unsuitable_for="不适合短期资金或保守型用户。",
        search_keywords=["混合", "偏股", "成长", "蓝筹"],
        name_keywords=["混合", "偏股", "成长", "蓝筹"],
        seed_codes=["005827", "110011"],
    ),
    "sector_theme": FundTypeRule(
        fund_type="行业主题型",
        reason="可作为高风险偏好下的补充研究方向，但需要重点检查集中度和回撤。",
        unsuitable_for="不适合作为新手的唯一研究对象。",
        search_keywords=["行业", "主题", "股票", "消费", "科技", "医药", "新能源"],
        name_keywords=["行业", "主题", "股票", "消费", "科技", "医药", "新能源"],
        seed_codes=[],
    ),
}


def match_fund_type_rules(profile: InvestorPreferenceProfile) -> List[FundTypeRule]:
    rules: List[FundTypeRule] = []
    if profile.liquidity_need == "high" or profile.horizon == "short":
        rules.append(FUND_TYPE_RULES["money_short_bond"])

    if profile.risk_tolerance == "low":
        rules.append(FUND_TYPE_RULES["bond"])
    elif profile.risk_tolerance == "medium":
        rules.extend([FUND_TYPE_RULES["bond_plus"], FUND_TYPE_RULES["broad_index"]])
    else:
        rules.extend(
            [
                FUND_TYPE_RULES["broad_index"],
                FUND_TYPE_RULES["equity_hybrid"],
                FUND_TYPE_RULES["sector_theme"],
            ]
        )

    return _dedupe_rules(rules)


def rules_to_matches(rules: Iterable[FundTypeRule], profile: Optional[InvestorPreferenceProfile] = None) -> List[FundTypeMatch]:
    return [rule.to_match(profile, index) for index, rule in enumerate(rules)]


def select_type_rules(rules: List[FundTypeRule], selected_fund_type: str) -> List[FundTypeRule]:
    if not selected_fund_type:
        return rules[:1]
    selected = [
        rule
        for rule in rules
        if rule.fund_type == selected_fund_type or selected_fund_type in rule.fund_type
    ]
    return selected or rules[:1]


def _dedupe_rules(rules: Iterable[FundTypeRule]) -> List[FundTypeRule]:
    seen = set()
    result = []
    for rule in rules:
        if rule.fund_type in seen:
            continue
        seen.add(rule.fund_type)
        result.append(rule)
    return result


def _fit_score(rule: FundTypeRule, profile: Optional[InvestorPreferenceProfile], rank: int) -> float:
    score = 88.0 - rank * 8
    if not profile:
        return max(score, 50.0)
    if rule.fund_type == "货币型 / 短债型" and (profile.horizon == "short" or profile.liquidity_need == "high"):
        score += 8
    if rule.fund_type == "债券型" and profile.risk_tolerance == "low":
        score += 8
    if rule.fund_type == "债券型 / 固收+" and profile.risk_tolerance == "medium":
        score += 6
    if rule.fund_type == "宽基指数型" and profile.horizon == "long":
        score += 5
    if rule.fund_type in {"偏股混合型", "行业主题型"} and profile.risk_tolerance == "high":
        score += 6
    if profile.experience_level == "beginner" and rule.fund_type == "行业主题型":
        score -= 10
    if profile.horizon == "short" and rule.fund_type in {"宽基指数型", "偏股混合型", "行业主题型"}:
        score -= 12
    return min(100.0, max(score, 45.0))


def _basis(rule: FundTypeRule, profile: Optional[InvestorPreferenceProfile]) -> List[str]:
    basis = [rule.reason]
    if not profile:
        return basis
    if profile.risk_tolerance == "low":
        basis.append("用户画像偏保守，优先控制净值波动和最大回撤。")
    elif profile.risk_tolerance == "medium":
        basis.append("用户画像偏平衡，需要在回撤控制和收益弹性之间取舍。")
    else:
        basis.append("用户画像偏进取，可以研究权益敞口，但仍需检查回撤边界。")
    if profile.horizon == "short" or profile.liquidity_need == "high":
        basis.append("资金期限或流动性要求较高，短期资金不宜优先暴露在高波动方向。")
    if profile.experience_level == "beginner":
        basis.append("新手画像优先选择结构更清晰、解释成本更低的基金方向。")
    return basis[:4]


def _risk_flags(rule: FundTypeRule, profile: Optional[InvestorPreferenceProfile]) -> List[str]:
    flags = [rule.unsuitable_for]
    if not profile:
        return flags
    if profile.horizon == "short" and rule.fund_type in {"宽基指数型", "偏股混合型", "行业主题型"}:
        flags.append("短期资金遇到市场波动时，可能来不及等待净值修复。")
    if profile.risk_tolerance == "low" and rule.fund_type in {"偏股混合型", "行业主题型"}:
        flags.append("保守画像不应把权益或主题方向作为优先研究对象。")
    if profile.experience_level == "beginner" and rule.fund_type == "行业主题型":
        flags.append("行业主题型通常集中度更高，新手需要额外关注持仓和回撤。")
    return flags[:3]


def _missing_context(profile: Optional[InvestorPreferenceProfile]) -> List[str]:
    if not profile:
        return ["还需要确认资金期限、风险承受和流动性需求。"]
    missing = []
    if profile.risk_tolerance == "medium":
        missing.append("可补充最大可接受阶段性亏损幅度。")
    if profile.liquidity_need == "medium":
        missing.append("可确认这笔钱是否会用于生活、应急或短期支出。")
    if profile.investment_goal == "希望先找到值得进一步研究的基金候选":
        missing.append("可补充具体目标，例如备用金、养老、教育金或长期资产配置。")
    return missing[:3]
