from typing import List

from app.data_providers.base import FundDataProvider
from app.models import FundProfile, NavPoint


class AkshareFundDataProvider(FundDataProvider):
    """AKShare adapter.

    AKShare is imported lazily so the offline demo and tests still work before
    optional data dependencies are installed.
    """

    def search_funds(self, query: str) -> List[FundProfile]:
        akshare = _load_akshare()
        frame = akshare.fund_open_fund_daily_em()
        matches = frame[
            frame.astype(str).apply(
                lambda row: query in "".join(row.values.tolist()),
                axis=1,
            )
        ].head(20)
        return [self._profile_from_daily_row(row) for _, row in matches.iterrows()]

    def get_profile(self, code: str) -> FundProfile:
        akshare = _load_akshare()
        frame = akshare.fund_open_fund_daily_em()
        row = frame[frame["基金代码"].astype(str) == code]
        if row.empty:
            raise LookupError("未找到基金档案")
        return self._profile_from_daily_row(row.iloc[0])

    def get_nav_history(self, code: str) -> List[NavPoint]:
        akshare = _load_akshare()
        frame = akshare.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if frame.empty:
            raise LookupError("未找到基金净值")

        points: List[NavPoint] = []
        for _, row in frame.iterrows():
            date_value = str(row.get("净值日期") or row.get("日期"))
            unit_nav = float(row.get("单位净值"))
            accumulated_nav = float(row.get("累计净值", unit_nav))
            points.append(NavPoint(date=date_value, unit_nav=unit_nav, accumulated_nav=accumulated_nav))
        return points

    def _profile_from_daily_row(self, row: object) -> FundProfile:
        code = str(row.get("基金代码", ""))
        name = str(row.get("基金简称", ""))
        return FundProfile(
            code=code,
            name=name,
            fund_type=str(row.get("基金类型", "未知")),
            inception_date="待补充",
            manager="待补充",
            company="待补充",
            scale="待补充",
            purchase_status=str(row.get("申购状态", "待确认")),
            redeem_status=str(row.get("赎回状态", "待确认")),
            fee_note="费率以基金公司公告为准",
            benchmark="待补充",
        )


def _load_akshare():
    try:
        import akshare  # type: ignore
    except ImportError as exc:
        raise RuntimeError("AKShare 未安装，请先运行 pip install -r requirements.txt") from exc
    return akshare

