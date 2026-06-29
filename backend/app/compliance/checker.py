from typing import Dict, Iterable, List

DISCLAIMER = "仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"

ALLOWED_CONCLUSIONS = {
    "适合关注",
    "适合长期观察",
    "仅适合高风险用户",
    "不适合当前用户",
    "数据不足，暂不评价",
}

PROHIBITED_PHRASES = [
    "必买",
    "稳赚",
    "保证收益",
    "强烈推荐买入",
    "未来一定上涨",
    "一定会涨",
    "无风险",
    "保本保收益",
    "建议买入",
    "建议卖出",
]


def scan_text(text: str) -> List[str]:
    return [phrase for phrase in PROHIBITED_PHRASES if phrase in text]


def sanitize_text(text: str) -> str:
    sanitized = text
    replacements = {
        "强烈推荐买入": "可进一步研究",
        "建议买入": "可纳入观察",
        "建议卖出": "需重新评估持有理由",
        "必买": "不可仅凭单一指标决策",
        "稳赚": "收益存在不确定性",
        "保证收益": "不保证收益",
        "未来一定上涨": "未来表现存在不确定性",
        "一定会涨": "未来表现存在不确定性",
        "无风险": "风险较低但并非无风险",
        "保本保收益": "不承诺保本或收益",
    }
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


def enforce_report_compliance(report: Dict[str, object]) -> Dict[str, object]:
    """Normalize conclusion and remove prohibited wording from report strings."""
    checked = dict(report)
    conclusion = str(checked.get("conclusion") or "数据不足，暂不评价")
    if conclusion not in ALLOWED_CONCLUSIONS:
        checked["conclusion"] = "数据不足，暂不评价"

    for key, value in list(checked.items()):
        if isinstance(value, str):
            checked[key] = sanitize_text(value)
        elif isinstance(value, list):
            checked[key] = [sanitize_text(str(item)) for item in value]

    warnings = list(_as_list(checked.get("compliance_warnings")))
    text = _flatten_report_text(checked)
    blocked = scan_text(text)
    if blocked:
        warnings.append("报告曾包含不合规表述，已改写为研究参考口径。")

    if DISCLAIMER not in warnings:
        warnings.append(DISCLAIMER)
    checked["compliance_warnings"] = warnings
    return checked


def _flatten_report_text(report: Dict[str, object]) -> str:
    parts: List[str] = []
    for value in report.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return "\n".join(parts)


def _as_list(value: object) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]

