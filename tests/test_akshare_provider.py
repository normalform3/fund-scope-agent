import json
from pathlib import Path

import pandas as pd

from app.data_providers import akshare_provider
from app.data_providers.akshare_provider import AkshareFundDataProvider


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "akshare" / "110011_mapping.json"


class RecordedAkshare:
    def __init__(self, payload):
        self.payload = payload

    def fund_name_em(self):
        return pd.DataFrame(self.payload["fund_name_em"])

    def fund_individual_basic_info_xq(self, symbol: str):
        rows = self.payload["fund_individual_basic_info_xq"].get(symbol, [])
        return pd.DataFrame(rows)

    def fund_open_fund_daily_em(self):
        return pd.DataFrame(self.payload["fund_open_fund_daily_em"])

    def fund_purchase_em(self):
        return pd.DataFrame(self.payload["fund_purchase_em"])

    def fund_open_fund_info_em(self, symbol: str, indicator: str):
        rows = self.payload["fund_open_fund_info_em"].get(symbol, {}).get(indicator, [])
        return pd.DataFrame(rows)

    def fund_portfolio_hold_em(self, symbol: str, date: str):
        return pd.DataFrame(self.payload["fund_portfolio_hold_em"].get(symbol, []))

    def fund_portfolio_industry_allocation_em(self, symbol: str, date: str):
        return pd.DataFrame(
            self.payload["fund_portfolio_industry_allocation_em"].get(symbol, [])
        )

    def fund_individual_detail_info_xq(self, symbol: str):
        rows = self.payload["fund_individual_detail_info_xq"].get(symbol, [])
        return pd.DataFrame(rows)

    def fund_fee_em(self, symbol: str, indicator: str):
        frame = pd.DataFrame(self.payload["fund_fee_em"].get(indicator, []))
        if indicator == "交易状态" and not frame.empty:
            frame.columns = [int(column) for column in frame.columns]
        return frame


def _provider(monkeypatch) -> AkshareFundDataProvider:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fake_akshare = RecordedAkshare(payload)
    monkeypatch.setattr(akshare_provider, "_load_akshare", lambda: fake_akshare)
    return AkshareFundDataProvider()


def test_akshare_profile_mapping_merges_basic_realtime_and_purchase_rows(monkeypatch):
    provider = _provider(monkeypatch)

    profile = provider.get_profile("110011")

    assert profile.code == "110011"
    assert profile.name == "易方达中小盘混合"
    assert profile.fund_type == "偏股混合型"
    assert profile.inception_date == "2008-06-19"
    assert profile.manager == "张三"
    assert profile.company == "易方达基金"
    assert profile.scale == "120.34亿元"
    assert profile.purchase_status == "限大额"
    assert profile.redeem_status == "开放赎回"
    assert profile.fee_note == "0.12%"
    assert profile.benchmark == "沪深300指数收益率*70%+中债指数收益率*30%"
    assert profile.investment_objective == "在控制风险的前提下追求长期增值。"
    assert profile.investment_strategy == "精选具有竞争优势的权益资产。"
    assert profile.custodian == "中国工商银行"
    assert profile.rating == "三年五星"
    assert profile.data_source == "akshare:xueqiu/eastmoney"


def test_akshare_name_table_mapping_supports_search_list_and_profile_fallback(monkeypatch):
    provider = _provider(monkeypatch)

    listed = provider.list_funds(limit=1)
    searched = provider.search_funds("国开债")
    fallback_profile = provider.get_profile("003376")

    assert [profile.code for profile in listed] == ["110011"]
    assert [profile.code for profile in searched] == ["003376"]
    assert fallback_profile.name == "广发中债7-10年国开债指数"
    assert fallback_profile.fund_type == "债券型"
    assert fallback_profile.data_source == "akshare:fund_name_em"


def test_akshare_nav_mapping_uses_accumulated_nav_and_skips_incomplete_rows(monkeypatch):
    provider = _provider(monkeypatch)

    points = provider.get_nav_history("110011")

    assert [point.date for point in points] == ["2024-01-02", "2024-01-03"]
    assert points[0].unit_nav == 1.0
    assert points[0].accumulated_nav == 2.0
    assert points[1].unit_nav == 1.01
    assert points[1].accumulated_nav == 2.03


def test_akshare_holdings_mapping_keeps_latest_period_and_numeric_fields(monkeypatch):
    provider = _provider(monkeypatch)

    holdings = provider.get_holdings("110011")

    assert [holding.stock_code for holding in holdings] == ["600519", "00700"]
    assert holdings[0].period == "2024年2季度"
    assert holdings[0].ratio == 8.1
    assert holdings[0].shares == 73.0
    assert holdings[0].market_value == 116000.0


def test_akshare_industry_mapping_keeps_latest_report_date(monkeypatch):
    provider = _provider(monkeypatch)

    allocations = provider.get_industry_allocation("110011")

    assert len(allocations) == 1
    assert allocations[0].industry == "信息技术"
    assert allocations[0].ratio == 18.2
    assert allocations[0].market_value == 250000.5
    assert allocations[0].report_date == "2024-06-30"


def test_akshare_fee_mapping_handles_detail_and_table_shapes(monkeypatch):
    provider = _provider(monkeypatch)

    fees = provider.get_fees("110011")
    fee_map = {(fee.category, fee.condition): fee.value for fee in fees}

    assert fee_map[("运作费用", "管理费率")] == "1.20%"
    assert fee_map[("运作费用", "托管费率")] == "0.20%"
    assert fee_map[("交易状态", "申购状态")] == "开放申购"
    assert fee_map[("交易状态", "赎回状态")] == "开放赎回"
    assert fee_map[("赎回费率", "小于7日")] == "1.50%"
