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
            "000198": FundProfile(
                code="000198",
                name="天弘余额宝货币（示例）",
                fund_type="货币型",
                inception_date="2013-05-29",
                manager="示例基金经理",
                company="天弘基金（示例）",
                scale="约 6000 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="活期存款利率（税后）",
                investment_objective="示例：在控制流动性风险的前提下追求稳定收益。",
                investment_strategy="示例：投资于短期货币市场工具。",
                custodian="示例托管银行",
                rating="示例数据",
                data_source="sample",
            ),
            "003376": FundProfile(
                code="003376",
                name="广发中债7-10年国开债指数（示例）",
                fund_type="债券型",
                inception_date="2016-09-26",
                manager="示例基金经理",
                company="广发基金（示例）",
                scale="约 55 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="中债-7-10年国开行债券指数收益率",
                investment_objective="示例：力争跟踪债券指数表现。",
                investment_strategy="示例：主要投资政策性金融债。",
                custodian="示例托管银行",
                rating="示例数据",
                data_source="sample",
            ),
            "110020": FundProfile(
                code="110020",
                name="易方达沪深300ETF联接（示例）",
                fund_type="指数型",
                inception_date="2009-08-26",
                manager="示例基金经理",
                company="易方达基金（示例）",
                scale="约 210 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="沪深300指数收益率 * 95% + 活期存款利率 * 5%",
                investment_objective="示例：紧密跟踪沪深300指数表现。",
                investment_strategy="示例：通过目标 ETF 获取宽基指数敞口。",
                custodian="示例托管银行",
                rating="示例数据",
                data_source="sample",
            ),
            "005827": FundProfile(
                code="005827",
                name="易方达蓝筹精选混合（示例）",
                fund_type="偏股混合型",
                inception_date="2018-09-05",
                manager="示例基金经理",
                company="易方达基金（示例）",
                scale="约 430 亿元（示例数据）",
                purchase_status="开放申购",
                redeem_status="开放赎回",
                fee_note="费率以基金公司公告为准",
                benchmark="沪深300指数收益率 * 70% + 恒生指数收益率 * 20% + 中债指数收益率 * 10%",
                investment_objective="示例：通过权益资产精选追求长期增值。",
                investment_strategy="示例：精选具有竞争优势的权益资产。",
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

    def list_funds(self, limit: int = 100) -> List[FundProfile]:
        return list(self._profiles.values())[:limit]

    def get_profile(self, code: str) -> FundProfile:
        if code not in self._profiles:
            raise LookupError("未找到基金档案")
        return self._profiles[code]

    def get_nav_history(self, code: str) -> List[NavPoint]:
        if code not in self._profiles:
            raise LookupError("未找到基金净值")
        return _build_sample_nav(*_sample_nav_profile(code))

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


def _sample_nav_profile(code: str):
    profiles = {
        "000198": (2, 0.00008, 0.00035, 0.0),
        "003376": (4, 0.00016, 0.0012, -0.002),
        "110020": (6, 0.00028, 0.0032, -0.006),
        "005827": (8, 0.00036, 0.0048, -0.009),
        "000001": (7, 0.00032, 0.0042, -0.008),
        "110011": (0, 0.00035, 0.0040, -0.012),
    }
    return profiles.get(code, (5, 0.00025, 0.0030, -0.006))


def _build_sample_nav(seed: int, trend: float, cycle_scale: float, shock_scale: float) -> List[NavPoint]:
    start = date(2021, 1, 4)
    points: List[NavPoint] = []
    value = 1.0 + seed * 0.01
    for day in range(0, 860):
        current = start + timedelta(days=day)
        if current.weekday() >= 5:
            continue
        cycle = math.sin((day + seed) / 27) * cycle_scale
        shock = shock_scale if 340 < day < 410 else 0.0
        rebound = abs(shock_scale) * 0.72 if 520 < day < 590 else 0.0
        value = max(0.5, value * (1 + trend + cycle + shock + rebound))
        points.append(
            NavPoint(
                date=current.isoformat(),
                unit_nav=round(value, 4),
                accumulated_nav=round(value * 1.08, 4),
            )
        )
    return points
