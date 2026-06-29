import math
from datetime import date, timedelta
from typing import Dict, List

from app.data_providers.base import FundDataProvider
from app.models import FundProfile, NavPoint


class SampleFundDataProvider(FundDataProvider):
    """Offline provider used for demos, tests, and external API failures."""

    def __init__(self) -> None:
        self._profiles: Dict[str, FundProfile] = {
            "110011": FundProfile(
                code="110011",
                name="易方达中小盘混合（示例）",
                fund_type="偏股混合型",
                inception_date="2008-06-19",
                manager="示例基金经理",
                company="易方达基金（示例）",
                scale="约 120 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="沪深300指数收益率 * 70% + 中债指数收益率 * 30%",
            ),
            "000001": FundProfile(
                code="000001",
                name="华夏成长混合（示例）",
                fund_type="混合型",
                inception_date="2001-12-18",
                manager="示例基金经理",
                company="华夏基金（示例）",
                scale="约 80 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="中证800指数收益率 * 80% + 中债指数收益率 * 20%",
            ),
        }

    def search_funds(self, query: str) -> List[FundProfile]:
        normalized = query.strip().lower()
        if not normalized:
            return list(self._profiles.values())
        return [
            profile
            for profile in self._profiles.values()
            if normalized in profile.code.lower() or normalized in profile.name.lower()
        ]

    def get_profile(self, code: str) -> FundProfile:
        if code not in self._profiles:
            raise LookupError("未找到基金档案")
        return self._profiles[code]

    def get_nav_history(self, code: str) -> List[NavPoint]:
        if code not in self._profiles:
            raise LookupError("未找到基金净值")
        return _build_sample_nav(seed=0 if code == "110011" else 7)


def _build_sample_nav(seed: int) -> List[NavPoint]:
    start = date(2021, 1, 4)
    points: List[NavPoint] = []
    value = 1.0 + seed * 0.01
    for day in range(0, 860):
        current = start + timedelta(days=day)
        if current.weekday() >= 5:
            continue
        trend = 0.00035
        cycle = math.sin((day + seed) / 27) * 0.004
        shock = -0.012 if 340 < day < 410 else 0.0
        rebound = 0.009 if 520 < day < 590 else 0.0
        value = max(0.5, value * (1 + trend + cycle + shock + rebound))
        points.append(
            NavPoint(
                date=current.isoformat(),
                unit_nav=round(value, 4),
                accumulated_nav=round(value * 1.08, 4),
            )
        )
    return points

