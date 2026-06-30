from dataclasses import dataclass
from typing import Dict, Iterable, List

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

    def to_match(self) -> FundTypeMatch:
        return FundTypeMatch(
            fund_type=self.fund_type,
            reason=self.reason,
            unsuitable_for=self.unsuitable_for,
            search_keywords=self.search_keywords,
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


def rules_to_matches(rules: Iterable[FundTypeRule]) -> List[FundTypeMatch]:
    return [rule.to_match() for rule in rules]


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
