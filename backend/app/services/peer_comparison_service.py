from typing import Dict, List, Optional, Tuple

from app.metrics.calculator import calculate_risk_metrics
from app.models import FundProfile, RiskMetrics
from app.services.fund_service import FundService

DEFAULT_SCAN_LIMIT = 30
DEFAULT_MAX_ITEMS = 8


class PeerComparisonService:
    """Build deterministic same-category metric comparisons."""

    def __init__(self, fund_service: Optional[FundService] = None) -> None:
        self.fund_service = fund_service or FundService()

    def compare(self, code: str, scan_limit: int = DEFAULT_SCAN_LIMIT, max_items: int = DEFAULT_MAX_ITEMS) -> Dict[str, object]:
        target_profile = self.fund_service.get_profile(code)
        target_bucket = _fund_type_bucket(target_profile.fund_type)
        scanned_profiles = self.fund_service.list_funds(scan_limit)
        peer_profiles = _select_peer_profiles(target_profile, scanned_profiles, target_bucket, max_items)

        items: List[Dict[str, object]] = []
        skipped: List[str] = []
        for profile in peer_profiles:
            try:
                metrics = calculate_risk_metrics(self.fund_service.get_nav_history(profile.code))
            except Exception as exc:
                skipped.append("%s %s：净值数据获取失败（%s）。" % (profile.code, profile.name, exc))
                continue
            items.append(_comparison_item(profile, metrics, profile.code == target_profile.code))

        ranks = _target_ranks(items)
        data_notes = _data_notes(
            target_profile=target_profile,
            target_bucket=target_bucket,
            scan_limit=scan_limit,
            scanned_count=len(scanned_profiles),
            matched_count=len(peer_profiles),
            compared_count=len(items),
            skipped=skipped,
        )

        return {
            "target": target_profile.to_dict(),
            "category": {
                "fund_type": target_profile.fund_type,
                "bucket": target_bucket,
                "matching_rule": "按基金类型归入同类桶后比较，暂不使用 LLM 判断同类。",
            },
            "items": items,
            "ranks": ranks,
            "data_notes": data_notes,
            "compliance_warnings": ["仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"],
        }

    def compare_codes(self, codes: List[str]) -> Dict[str, object]:
        requested_codes = _normalize_codes(codes)
        items: List[Dict[str, object]] = []
        skipped: List[str] = []
        for code in requested_codes:
            try:
                profile = self.fund_service.get_profile(code)
                metrics = calculate_risk_metrics(self.fund_service.get_nav_history(code))
            except Exception as exc:
                skipped.append("%s：数据获取失败（%s）。" % (code, exc))
                continue
            items.append(_comparison_item(profile, metrics, False))

        rankings = _metric_rankings(items)
        return {
            "watchlist": {
                "codes": requested_codes,
                "persistence": "not_persisted",
                "note": "当前比较基于本次请求中的基金代码，暂不保存为长期观察池。",
            },
            "items": items,
            "rankings": rankings,
            "data_notes": _watchlist_data_notes(len(requested_codes), len(items), skipped),
            "compliance_warnings": ["仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"],
        }


def _select_peer_profiles(
    target_profile: FundProfile,
    scanned_profiles: List[FundProfile],
    target_bucket: str,
    max_items: int,
) -> List[FundProfile]:
    selected: Dict[str, FundProfile] = {target_profile.code: target_profile}
    for profile in scanned_profiles:
        if len(selected) >= max_items:
            break
        if profile.code == target_profile.code:
            selected[profile.code] = target_profile
            continue
        if _fund_type_bucket(profile.fund_type) == target_bucket:
            selected[profile.code] = profile
    return list(selected.values())


def _fund_type_bucket(fund_type: str) -> str:
    text = (fund_type or "").strip()
    if "货币" in text:
        return "货币型"
    if "债" in text:
        return "债券型"
    if "指数" in text or "ETF" in text.upper():
        return "指数型"
    if "股票" in text:
        return "股票型"
    if "混合" in text:
        return "混合型"
    if "QDII" in text.upper() or "海外" in text:
        return "QDII"
    return text or "未知"


def _comparison_item(profile: FundProfile, metrics: RiskMetrics, is_target: bool) -> Dict[str, object]:
    return {
        "code": profile.code,
        "name": profile.name,
        "fund_type": profile.fund_type,
        "data_source": profile.data_source,
        "is_target": is_target,
        "observation_days": metrics.observation_days,
        "total_return": metrics.total_return,
        "annualized_return": metrics.annualized_return,
        "annualized_volatility": metrics.annualized_volatility,
        "max_drawdown": metrics.max_drawdown,
        "sharpe_ratio": metrics.sharpe_ratio,
        "warnings": metrics.warnings,
    }


def _normalize_codes(codes: List[str]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for code in codes:
        text = str(code).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def _target_ranks(items: List[Dict[str, object]]) -> Dict[str, object]:
    target = next((item for item in items if item["is_target"]), None)
    if not target:
        return {}
    metric_specs = {
        "total_return": True,
        "annualized_return": True,
        "annualized_volatility": False,
        "max_drawdown": True,
        "sharpe_ratio": True,
    }
    ranks: Dict[str, object] = {}
    for metric, higher_is_better in metric_specs.items():
        ranks[metric] = _rank_metric(items, target, metric, higher_is_better)
    return ranks


def _rank_metric(
    items: List[Dict[str, object]],
    target: Dict[str, object],
    metric: str,
    higher_is_better: bool,
) -> Dict[str, object]:
    comparable = [item for item in items if isinstance(item.get(metric), (float, int))]
    target_value = target.get(metric)
    if not isinstance(target_value, (float, int)) or not comparable:
        return {
            "rank": None,
            "count": len(comparable),
            "percentile": None,
            "direction": "higher" if higher_is_better else "lower",
            "note": "目标基金该指标缺失，无法计算同类位置。",
        }

    ordered = sorted(
        comparable,
        key=lambda item: item[metric],
        reverse=higher_is_better,
    )
    rank = next(index + 1 for index, item in enumerate(ordered) if item["is_target"])
    percentile = _percentile_from_rank(rank, len(ordered))
    return {
        "rank": rank,
        "count": len(ordered),
        "percentile": percentile,
        "direction": "higher" if higher_is_better else "lower",
        "note": _rank_note(metric, rank, len(ordered), percentile),
    }


def _metric_rankings(items: List[Dict[str, object]]) -> Dict[str, object]:
    metric_specs = {
        "total_return": True,
        "annualized_return": True,
        "annualized_volatility": False,
        "max_drawdown": True,
        "sharpe_ratio": True,
    }
    return {
        metric: _ranking_list(items, metric, higher_is_better)
        for metric, higher_is_better in metric_specs.items()
    }


def _ranking_list(items: List[Dict[str, object]], metric: str, higher_is_better: bool) -> Dict[str, object]:
    comparable = [item for item in items if isinstance(item.get(metric), (float, int))]
    ordered = sorted(comparable, key=lambda item: item[metric], reverse=higher_is_better)
    return {
        "direction": "higher" if higher_is_better else "lower",
        "count": len(ordered),
        "items": [
            {
                "rank": index + 1,
                "code": item["code"],
                "name": item["name"],
                "value": item[metric],
            }
            for index, item in enumerate(ordered)
        ],
    }


def _percentile_from_rank(rank: int, count: int) -> Optional[float]:
    if count <= 1:
        return None
    return (count - rank) / (count - 1)


def _rank_note(metric: str, rank: int, count: int, percentile: Optional[float]) -> str:
    labels = {
        "total_return": "累计收益",
        "annualized_return": "年化收益",
        "annualized_volatility": "年化波动率",
        "max_drawdown": "最大回撤控制",
        "sharpe_ratio": "夏普比率",
    }
    label = labels.get(metric, metric)
    if count <= 1 or percentile is None:
        return "%s 当前只有目标基金可比较，暂不能判断同类位置。" % label
    if percentile >= 0.66:
        band = "同类样本中相对靠前"
    elif percentile >= 0.33:
        band = "同类样本中处于中间区间"
    else:
        band = "同类样本中相对靠后"
    return "%s在 %s 只可比基金中排名第 %s，%s。" % (label, count, rank, band)


def _data_notes(
    target_profile: FundProfile,
    target_bucket: str,
    scan_limit: int,
    scanned_count: int,
    matched_count: int,
    compared_count: int,
    skipped: List[str],
) -> List[str]:
    notes = [
        "目标基金 %s 归入 %s 同类桶，基金类型原始值为 %s。"
        % (target_profile.code, target_bucket, target_profile.fund_type or "未知"),
        "本次最多扫描 %s 只基金，实际扫描 %s 只，进入同类候选 %s 只，完成指标比较 %s 只。"
        % (scan_limit, scanned_count, matched_count, compared_count),
        "同类划分为确定性规则，当前只按基金类型归桶，尚未纳入基金规模、指数基准、持仓风格或经理任期。",
    ]
    if compared_count < 3:
        notes.append("可比样本少于 3 只，同类位置只适合作为粗略参考。")
    notes.extend(skipped[:5])
    if len(skipped) > 5:
        notes.append("另有 %s 只同类候选因数据问题未纳入比较。" % (len(skipped) - 5))
    return notes


def _watchlist_data_notes(requested_count: int, compared_count: int, skipped: List[str]) -> List[str]:
    notes = [
        "本次收到 %s 只去重后的基金代码，完成 %s 只基金的横向指标比较。"
        % (requested_count, compared_count),
        "比较指标由历史净值确定性计算得出，未使用 LLM 排名或改写结论。",
        "当前为非持久化观察池模型，刷新页面或重新请求不会自动保留本次列表。",
    ]
    if compared_count < 2:
        notes.append("可比基金少于 2 只，暂不能形成有效横向比较。")
    notes.extend(skipped[:5])
    if len(skipped) > 5:
        notes.append("另有 %s 只基金因数据问题未纳入比较。" % (len(skipped) - 5))
    return notes
