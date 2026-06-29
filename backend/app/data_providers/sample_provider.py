import math
from datetime import date, timedelta
from typing import Dict, List

from app.data_providers.base import FundDataProvider
from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint


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
                investment_objective="示例：在控制风险的前提下追求长期增值。",
                investment_strategy="示例：精选具有竞争优势的权益资产。",
                custodian="示例托管银行",
                rating="示例数据",
                data_source="sample",
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
                investment_objective="示例：追求基金资产长期稳定增值。",
                investment_strategy="示例：权益和固收资产均衡配置。",
                custodian="示例托管银行",
                rating="示例数据",
                data_source="sample",
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

    def get_holdings(self, code: str) -> List[FundHolding]:
        if code not in self._profiles:
            raise LookupError("未找到基金持仓")
        return [
            FundHolding("000858", "五粮液（示例）", 9.82, 920.0, 141229.20, "2024年4季度"),
            FundHolding("00700", "腾讯控股（示例）", 9.60, 501.5, 138118.06, "2024年4季度"),
            FundHolding("600519", "贵州茅台（示例）", 8.10, 73.0, 116000.00, "2024年4季度"),
        ]

    def get_industry_allocation(self, code: str) -> List[IndustryAllocation]:
        if code not in self._profiles:
            raise LookupError("未找到行业配置")
        return [
            IndustryAllocation("必需消费品（示例）", 42.0, 5725984000.0, "2024-12-31"),
            IndustryAllocation("非必需消费品（示例）", 35.15, 4792501000.0, "2024-12-31"),
            IndustryAllocation("信息技术（示例）", 12.3, 1678000000.0, "2024-12-31"),
        ]

    def get_fees(self, code: str) -> List[FundFee]:
        if code not in self._profiles:
            raise LookupError("未找到费率")
        return [
            FundFee("交易状态", "申购状态", self._profiles[code].purchase_status),
            FundFee("交易状态", "赎回状态", self._profiles[code].redeem_status),
            FundFee("运作费用", "管理费率", "1.20%（示例）"),
            FundFee("运作费用", "托管费率", "0.20%（示例）"),
        ]


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
