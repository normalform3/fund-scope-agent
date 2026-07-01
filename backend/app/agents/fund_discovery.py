from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.agents.discovery_rules import (
    MAX_CANDIDATE_PROFILES,
    MAX_CODE_TABLE_FUNDS,
    MAX_SEARCH_TERMS,
    MIN_OBSERVATION_DAYS,
    RISK_LIMITS,
    FundTypeRule,
    match_fund_type_rules,
    rules_to_matches,
    select_type_rules,
)
from app.compliance.checker import DISCLAIMER, scan_text, sanitize_text
from app.metrics.calculator import calculate_risk_metrics
from app.models import FundCandidate, FundProfile, FundTypeMatch, InvestorPreferenceProfile
from app.services.fund_service import FundService
from app.services.llm_service import LLMService


class FundDiscoveryWorkflow:
    """Find research candidates before the single-fund checkup flow.

    V1 keeps the final matching and ranking deterministic. LLM parsing can be
    added ahead of `_build_profile` later without changing the API contract.
    """

    def __init__(self, fund_service: Optional[FundService] = None, llm_service: Optional[LLMService] = None) -> None:
        self.fund_service = fund_service or FundService()
        self.llm_service = llm_service or LLMService()

    def run(
        self,
        goal_text: str,
        answers: Optional[Dict[str, str]] = None,
        include_candidates: bool = False,
        selected_fund_type: str = "",
        refinement_text: str = "",
    ) -> Dict[str, object]:
        answers = answers or {}
        llm_hints, llm_note = self.llm_service.parse_discovery_profile(goal_text, answers, refinement_text)
        profile = _build_profile(goal_text, answers, llm_hints)
        fund_type_rules = match_fund_type_rules(profile)
        fund_type_matches = rules_to_matches(fund_type_rules, profile)
        stage = "candidate_refinement" if include_candidates else "type_match"
        data_notes: List[str] = [llm_note] if llm_note else []
        candidates: List[FundCandidate] = []
        selected_rules = select_type_rules(fund_type_rules, selected_fund_type)
        selected_matches = rules_to_matches(selected_rules, profile)
        if include_candidates:
            candidates, candidate_notes = self._select_candidates(profile, selected_rules, refinement_text)
            data_notes.extend(candidate_notes)
        visible_matches = selected_matches if include_candidates else fund_type_matches
        decision_basis = _decision_basis(profile, visible_matches, candidates)
        llm_explanation, llm_questions, llm_used, explanation_note = _explain_discovery(
            self.llm_service,
            profile,
            visible_matches,
            candidates,
            include_candidates,
        )
        if explanation_note:
            data_notes.append(explanation_note)
        payload = {
            "stage": stage,
            "profile": profile.to_dict(),
            "fund_type_matches": [item.to_dict() for item in fund_type_matches],
            "candidates": [item.to_dict() for item in candidates],
            "clarifying_questions": _dedupe_text(_clarifying_questions(profile) + llm_questions)[:3],
            "summary": _build_summary(profile, visible_matches, candidates, include_candidates),
            "llm_explanation": llm_explanation or _fallback_explanation(profile, visible_matches, candidates, include_candidates),
            "llm_used": llm_used,
            "decision_basis": decision_basis,
            "data_notes": data_notes,
            "compliance_warnings": [DISCLAIMER],
        }
        return _sanitize_payload(payload)

    def _select_candidates(
        self,
        profile: InvestorPreferenceProfile,
        fund_type_rules: List[FundTypeRule],
        refinement_text: str,
    ) -> Tuple[List[FundCandidate], List[str]]:
        raw_profiles, data_notes = self._search_candidate_profiles(fund_type_rules)
        scored: List[Tuple[float, FundCandidate]] = []
        for raw_profile in raw_profiles:
            try:
                profile_detail = self.fund_service.get_profile(raw_profile.code)
                nav_points = self.fund_service.get_nav_history(raw_profile.code)
            except Exception as exc:
                data_notes.append("%s 数据不足，未纳入候选：%s" % (raw_profile.code, exc))
                continue

            metrics = calculate_risk_metrics(nav_points)
            if metrics.observation_days < MIN_OBSERVATION_DAYS:
                data_notes.append("%s 历史净值样本不足，未纳入候选。" % profile_detail.code)
                continue

            match_score = _fund_type_score(profile_detail, fund_type_rules)
            if match_score <= 0:
                continue

            risk_ok, risk_note = _risk_is_acceptable(profile, metrics)
            if not risk_ok:
                data_notes.append("%s %s，未纳入候选。" % (profile_detail.code, risk_note))
                continue

            if _is_purchase_closed(profile_detail):
                data_notes.append("%s 当前申购状态不适合纳入候选观察。" % profile_detail.code)
                continue

            score = match_score + _risk_score(profile.risk_tolerance, metrics) + _refinement_score(profile_detail, metrics, refinement_text)
            scored.append((score, _build_candidate(profile_detail, metrics, risk_note)))

        scored.sort(key=lambda item: item[0], reverse=True)
        candidates = [item[1] for item in scored[:3]]
        if not candidates:
            data_notes.append("当前数据源未找到足够匹配的候选基金，请放宽条件或稍后重试。")
        return candidates, _dedupe_text(data_notes)

    def _search_candidate_profiles(self, fund_type_rules: List[FundTypeRule]) -> Tuple[List[FundProfile], List[str]]:
        profiles: List[FundProfile] = []
        seen_codes: Set[str] = set()
        data_notes: List[str] = []

        def add_profile(candidate: FundProfile) -> bool:
            if candidate.code in seen_codes:
                return len(profiles) >= MAX_CANDIDATE_PROFILES
            seen_codes.add(candidate.code)
            profiles.append(candidate)
            return len(profiles) >= MAX_CANDIDATE_PROFILES

        for code in _candidate_seed_codes(fund_type_rules):
            try:
                if add_profile(self.fund_service.get_profile(code)):
                    return profiles, data_notes
            except Exception as exc:
                data_notes.append("种子基金 %s 档案获取失败：%s" % (code, exc))

        for keyword in _candidate_search_terms(fund_type_rules)[:MAX_SEARCH_TERMS]:
            try:
                found = self.fund_service.search_funds(keyword)
            except Exception as exc:
                data_notes.append("搜索 %s 失败：%s" % (keyword or "全部基金", exc))
                continue
            for profile in found:
                if add_profile(profile):
                    return profiles, data_notes

        try:
            code_table_profiles = self.fund_service.list_funds(MAX_CODE_TABLE_FUNDS)
        except Exception as exc:
            data_notes.append("基金代码表召回失败：%s" % exc)
            return profiles, data_notes

        for profile in code_table_profiles:
            if not _candidate_matches_rules(profile, fund_type_rules):
                continue
            if add_profile(profile):
                return profiles, data_notes
        return profiles, data_notes


def _build_profile(goal_text: str, answers: Dict[str, str], llm_hints: Optional[Dict[str, str]] = None) -> InvestorPreferenceProfile:
    llm_hints = llm_hints or {}
    text = " ".join([goal_text] + [str(value) for value in answers.values()]).strip()
    risk_tolerance = _normalize_choice(
        answers.get("risk_tolerance") or llm_hints.get("risk_tolerance"),
        {"low": "low", "medium": "medium", "high": "high", "保守": "low", "稳健": "low", "平衡": "medium", "进取": "high"},
    )
    if not risk_tolerance:
        risk_tolerance = _infer_risk_tolerance(text)

    horizon = _normalize_choice(
        answers.get("horizon") or llm_hints.get("horizon"),
        {"short": "short", "medium": "medium", "long": "long", "短期": "short", "中期": "medium", "长期": "long"},
    )
    if not horizon:
        horizon = _infer_horizon(text)

    liquidity_need = _normalize_choice(
        answers.get("liquidity_need") or llm_hints.get("liquidity_need"),
        {"high": "high", "medium": "medium", "low": "low", "高": "high", "中": "medium", "低": "low"},
    )
    if not liquidity_need:
        liquidity_need = _infer_liquidity(text)

    experience_level = _normalize_choice(
        answers.get("experience_level") or llm_hints.get("experience_level"),
        {"beginner": "beginner", "some": "some", "experienced": "experienced", "新手": "beginner", "有经验": "experienced"},
    )
    if not experience_level:
        experience_level = "beginner" if _contains_any(text, ["新手", "小白", "第一次", "不懂"]) else "some"

    investment_goal = answers.get("investment_goal") or llm_hints.get("investment_goal") or goal_text.strip() or "希望先找到值得进一步研究的基金候选"
    max_loss_tolerance = _normalize_loss_tolerance(
        answers.get("max_loss_tolerance") or llm_hints.get("max_loss_tolerance")
    )
    investment_horizon_months = _normalize_positive_int(
        answers.get("investment_horizon_months") or llm_hints.get("investment_horizon_months")
    )
    can_delay_use = _normalize_optional_bool(answers.get("can_delay_use") or llm_hints.get("can_delay_use"))
    money_purpose = _normalize_money_purpose(answers.get("money_purpose") or llm_hints.get("money_purpose"))
    notes = _profile_notes(risk_tolerance, horizon, liquidity_need, experience_level)
    if max_loss_tolerance is not None:
        notes.append("用户可接受的阶段性亏损约为 %.0f%%，候选会据此额外过滤最大回撤。" % (max_loss_tolerance * 100))
    if investment_horizon_months is not None:
        notes.append("用户预计持有期限约 %s 个月。" % investment_horizon_months)
    if can_delay_use is False:
        notes.append("用户这笔钱到期不方便延期使用，体检报告会额外关注回撤修复压力。")
    elif can_delay_use is True:
        notes.append("用户这笔钱到期有一定延期空间，仍需结合回撤修复周期观察。")
    if money_purpose:
        notes.append("资金用途为%s，体检报告会结合用途解释回撤和波动压力。" % _money_purpose_label(money_purpose))
    notes.extend(_split_llm_list(llm_hints.get("notes", ""))[:2])
    return InvestorPreferenceProfile(
        investment_goal=investment_goal,
        horizon=horizon,
        risk_tolerance=risk_tolerance,
        liquidity_need=liquidity_need,
        experience_level=experience_level,
        preferred_fund_types=_split_llm_list(llm_hints.get("preferred_fund_types", "")),
        notes=notes,
        max_loss_tolerance=max_loss_tolerance,
        investment_horizon_months=investment_horizon_months,
        can_delay_use=can_delay_use,
        money_purpose=money_purpose,
    )


def _build_candidate(profile: FundProfile, metrics: object, risk_note: str) -> FundCandidate:
    reason_parts = [
        "%s 与当前基金类型方向较匹配，可作为候选观察对象。" % profile.fund_type,
        "历史样本覆盖 %s 个交易日。" % metrics.observation_days,
    ]
    if metrics.max_drawdown is not None:
        reason_parts.append("样本期最大回撤为 %.2f%%。" % (metrics.max_drawdown * 100))
    if metrics.annualized_volatility is not None:
        reason_parts.append("年化波动率为 %.2f%%。" % (metrics.annualized_volatility * 100))

    risk_notes = [risk_note, "候选结果仅用于后续体检分析，不代表买入、卖出或持有建议。"]
    basis = [
        "%s 与所选研究方向匹配。" % profile.fund_type,
        "历史净值样本达到 %s 个交易日，满足最小样本要求。" % metrics.observation_days,
        risk_note,
    ]
    if metrics.max_drawdown is not None:
        basis.append("最大回撤 %.2f%% 已通过当前风险画像过滤。" % (metrics.max_drawdown * 100))
    if metrics.annualized_volatility is not None:
        basis.append("年化波动率 %.2f%% 已通过当前风险画像过滤。" % (metrics.annualized_volatility * 100))
    return FundCandidate(
        code=profile.code,
        name=profile.name,
        fund_type=profile.fund_type,
        reason=" ".join(reason_parts),
        risk_notes=risk_notes,
        data_source=profile.data_source,
        next_action="生成体检报告",
        observation_days=metrics.observation_days,
        annualized_volatility=metrics.annualized_volatility,
        max_drawdown=metrics.max_drawdown,
        basis=basis[:5],
    )


def _risk_is_acceptable(profile: InvestorPreferenceProfile, metrics: object) -> Tuple[bool, str]:
    limits = RISK_LIMITS.get(profile.risk_tolerance, RISK_LIMITS["medium"])
    if metrics.annualized_volatility is None or metrics.max_drawdown is None:
        return False, "风险指标不完整，暂不纳入候选。"
    if profile.max_loss_tolerance is not None and abs(metrics.max_drawdown) > profile.max_loss_tolerance:
        return False, "最大回撤超过用户可接受的阶段性亏损 %.0f%%" % (profile.max_loss_tolerance * 100)
    if metrics.annualized_volatility > limits["max_volatility"]:
        return False, "年化波动率超过当前风险画像边界。"
    if metrics.max_drawdown < limits["max_drawdown"]:
        return False, "最大回撤超过当前风险画像边界。"
    if profile.risk_tolerance == "high":
        return True, "该候选仍可能出现较大净值波动，需要重点查看回撤和持仓集中度。"
    if profile.risk_tolerance == "low":
        return True, "该候选通过当前保守画像的波动和回撤过滤，但仍需查看底层资产风险。"
    return True, "该候选通过当前平衡画像的波动和回撤过滤，仍需结合持仓和费用继续分析。"


def _risk_score(risk_tolerance: str, metrics: object) -> float:
    limits = RISK_LIMITS.get(risk_tolerance, RISK_LIMITS["medium"])
    drawdown_room = abs(limits["max_drawdown"] - (metrics.max_drawdown or limits["max_drawdown"]))
    volatility_room = limits["max_volatility"] - (metrics.annualized_volatility or limits["max_volatility"])
    return max(0.0, drawdown_room * 2 + volatility_room)


def _refinement_score(profile: FundProfile, metrics: object, refinement_text: str) -> float:
    if not refinement_text:
        return 0.0
    score = 0.0
    text = "%s %s %s %s" % (profile.name, profile.fund_type, profile.scale, profile.fee_note)
    if _contains_any(refinement_text, ["波动小", "回撤小", "稳一点", "稳健"]) and metrics.max_drawdown is not None:
        score += max(0.0, 0.2 + metrics.max_drawdown)
    if _contains_any(refinement_text, ["指数", "宽基"]) and _contains_any(text, ["指数", "沪深300", "中证"]):
        score += 2.0
    if _contains_any(refinement_text, ["债", "固收"]) and _contains_any(text, ["债", "固收"]):
        score += 2.0
    if _contains_any(refinement_text, ["规模", "大厂", "大型"]) and not _contains_any(profile.scale, ["待补充", "示例数据"]):
        score += 0.5
    if _contains_any(refinement_text, ["费率", "费用", "低费"]):
        score += 0.2
    return score


def _fund_type_score(profile: FundProfile, fund_type_rules: List[FundTypeRule]) -> float:
    text = "%s %s %s" % (profile.name, profile.fund_type, profile.benchmark)
    score = 0.0
    for index, rule in enumerate(fund_type_rules):
        if _fund_matches_type(text, rule):
            score = max(score, 10.0 - index)
    return score


def _fund_matches_type(text: str, rule: FundTypeRule) -> bool:
    return _contains_any(text, rule.name_keywords)


def _candidate_matches_rules(profile: FundProfile, fund_type_rules: List[FundTypeRule]) -> bool:
    text = "%s %s %s" % (profile.name, profile.fund_type, profile.benchmark)
    return any(_fund_matches_type(text, rule) for rule in fund_type_rules)


def _candidate_search_terms(fund_type_rules: List[FundTypeRule]) -> List[str]:
    terms: List[str] = []
    for rule in fund_type_rules:
        terms.append(rule.fund_type)
        terms.extend(rule.search_keywords)
        terms.extend(rule.name_keywords)
    return _dedupe_text(terms)


def _candidate_seed_codes(fund_type_rules: List[FundTypeRule]) -> List[str]:
    codes: List[str] = []
    for rule in fund_type_rules:
        codes.extend(rule.seed_codes)
    return _dedupe_text(codes)


def _is_purchase_closed(profile: FundProfile) -> bool:
    text = "%s %s" % (profile.purchase_status, profile.redeem_status)
    return _contains_any(text, ["暂停申购", "封闭", "不可申购"])


def _infer_risk_tolerance(text: str) -> str:
    if _contains_any(text, ["保守", "稳健", "低风险", "亏损少", "不能亏", "少亏", "回撤小"]):
        return "low"
    if _contains_any(text, ["高风险", "进取", "高收益", "成长", "权益", "股票", "行业", "主题"]):
        return "high"
    return "medium"


def _infer_horizon(text: str) -> str:
    if _contains_any(text, ["短期", "三个月", "3个月", "半年", "随时", "备用金"]):
        return "short"
    if _contains_any(text, ["长期", "三年", "3年", "五年", "5年", "养老"]):
        return "long"
    return "medium"


def _infer_liquidity(text: str) -> str:
    if _contains_any(text, ["随时", "流动性", "备用金", "短期", "取出"]):
        return "high"
    if _contains_any(text, ["长期不用", "不急用", "三年", "五年"]):
        return "low"
    return "medium"


def _profile_notes(risk_tolerance: str, horizon: str, liquidity_need: str, experience_level: str) -> List[str]:
    notes = []
    if experience_level == "beginner":
        notes.append("新手画像优先选择更容易解释、数据更透明的基金类型。")
    if risk_tolerance == "low":
        notes.append("当前风险偏好偏保守，候选会避开高波动权益或主题型基金。")
    elif risk_tolerance == "high":
        notes.append("当前风险偏好偏进取，但候选仍会保留回撤和波动过滤。")
    if horizon == "short" or liquidity_need == "high":
        notes.append("资金期限或流动性要求较高，候选会优先控制波动。")
    return notes


def _clarifying_questions(profile: InvestorPreferenceProfile) -> List[str]:
    questions = []
    if profile.investment_goal == "希望先找到值得进一步研究的基金候选":
        questions.append("这笔资金预计多久不用？")
    if profile.risk_tolerance == "medium":
        questions.append("如果阶段性亏损超过 15%，你是否还能继续观察？")
    if profile.liquidity_need == "medium":
        questions.append("这笔钱是否需要随时取出用于生活或应急？")
    return questions[:3]


def _decision_basis(
    profile: InvestorPreferenceProfile,
    fund_type_matches: List[FundTypeMatch],
    candidates: List[FundCandidate],
) -> List[str]:
    basis = [
        "风险画像：%s，资金期限：%s，流动性需求：%s。"
        % (_risk_label(profile.risk_tolerance), _horizon_label(profile.horizon), _liquidity_label(profile.liquidity_need)),
        "基金大类由规则模块根据风险、期限、流动性和经验水平匹配，不由 LLM 直接推荐。",
    ]
    if profile.max_loss_tolerance is not None:
        basis.append("最大可接受阶段性亏损：%.0f%%。" % (profile.max_loss_tolerance * 100))
    if profile.can_delay_use is False:
        basis.append("这笔钱到期不方便延期使用，后续体检需重点看回撤是否能在期限内修复。")
    elif profile.can_delay_use is True:
        basis.append("这笔钱到期有一定延期空间，但仍需持续观察回撤修复压力。")
    if profile.money_purpose:
        basis.append("资金用途：%s。" % _money_purpose_label(profile.money_purpose))
    if fund_type_matches:
        basis.append("当前优先研究方向：%s。" % "、".join(match.fund_type for match in fund_type_matches[:3]))
    if candidates:
        basis.append("候选基金已通过历史净值样本、基金类型、波动率、最大回撤和申购状态过滤。")
    else:
        basis.append("具体候选需在用户选择研究方向并补充要求后再筛选。")
    return basis


def _explain_discovery(
    llm_service: object,
    profile: InvestorPreferenceProfile,
    fund_type_matches: List[FundTypeMatch],
    candidates: List[FundCandidate],
    include_candidates: bool,
) -> Tuple[str, List[str], bool, str]:
    explain = getattr(llm_service, "explain_discovery_decision", None)
    if not callable(explain):
        return "", [], False, ""
    try:
        return explain(
            profile.to_dict(),
            [item.to_dict() for item in fund_type_matches],
            [item.to_dict() for item in candidates],
            include_candidates,
        )
    except Exception as exc:
        return "", [], False, "LLM 解释失败，已使用规则说明：%s" % str(exc)


def _fallback_explanation(
    profile: InvestorPreferenceProfile,
    fund_type_matches: List[FundTypeMatch],
    candidates: List[FundCandidate],
    include_candidates: bool,
) -> str:
    fund_types = "、".join(match.fund_type for match in fund_type_matches[:3]) or "暂无匹配方向"
    if include_candidates and candidates:
        return (
            "本次先按%s风险画像聚焦%s，再用历史净值样本、波动率、最大回撤和申购状态过滤候选。"
            "候选只表示可进一步研究，不构成投资建议。"
            % (_risk_label(profile.risk_tolerance), fund_types)
        )
    return (
        "本次按%s风险画像、%s资金期限和%s流动性需求匹配%s。"
        "下一步可选择一个方向，再补充费用、波动或指数偏好来筛选候选观察基金。"
        % (
            _risk_label(profile.risk_tolerance),
            _horizon_label(profile.horizon),
            _liquidity_label(profile.liquidity_need),
            fund_types,
        )
    )


def _build_summary(
    profile: InvestorPreferenceProfile,
    fund_type_matches: List[FundTypeMatch],
    candidates: List[FundCandidate],
    include_candidates: bool,
) -> str:
    fund_types = "、".join(match.fund_type for match in fund_type_matches[:3])
    if not include_candidates:
        return "已根据%s风险画像推荐基金大类：%s。可选择一个方向后继续补充要求，再筛选候选基金。" % (
            _risk_label(profile.risk_tolerance),
            fund_types,
        )
    if candidates:
        return "已根据%s风险画像匹配 %s，并筛出 %s 支候选观察基金，可继续生成单基金体检报告。" % (
            _risk_label(profile.risk_tolerance),
            fund_types,
            len(candidates),
        )
    return "已根据%s风险画像匹配 %s，但当前数据源没有找到足够可靠的候选。" % (
        _risk_label(profile.risk_tolerance),
        fund_types,
    )


def _risk_label(value: str) -> str:
    return {"low": "保守型", "medium": "平衡型", "high": "进取型"}.get(value, "平衡型")


def _horizon_label(value: str) -> str:
    return {"short": "短期", "medium": "中期", "long": "长期"}.get(value, "中期")


def _liquidity_label(value: str) -> str:
    return {"high": "高", "medium": "中等", "low": "低"}.get(value, "中等")


def _normalize_choice(value: Optional[str], mapping: Dict[str, str]) -> str:
    if not value:
        return ""
    normalized = str(value).strip().lower()
    for source, target in mapping.items():
        if normalized == source.lower() or source in str(value):
            return target
    return normalized if normalized in {"low", "medium", "high", "short", "long", "beginner", "some", "experienced"} else ""


def _normalize_loss_tolerance(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = abs(float(value))
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return min(number, 1.0)


def _normalize_positive_int(value: object) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalize_optional_bool(value: object) -> Optional[bool]:
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


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _split_llm_list(text: str) -> List[str]:
    if not text:
        return []
    normalized = text.replace("，", ",").replace("；", ",").replace("、", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _dedupe_text(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _sanitize_payload(payload: Dict[str, object]) -> Dict[str, object]:
    checked = _sanitize_value(payload)
    text = str(checked)
    warnings = list(checked.get("compliance_warnings", []))
    if scan_text(text):
        warnings.append("候选输出曾包含不合规表述，已改写为研究参考口径。")
    if DISCLAIMER not in warnings:
        warnings.append(DISCLAIMER)
    checked["compliance_warnings"] = _dedupe_text(warnings)
    return checked


def _sanitize_value(value):
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    return value
