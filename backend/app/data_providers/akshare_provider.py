from datetime import date
import re
from typing import Dict, List, Optional

from app.data_providers.base import FundDataProvider
from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint


class AkshareFundDataProvider(FundDataProvider):
    """AKShare adapter for public fund data.

    AKShare is imported lazily so the offline demo and tests still work before
    optional data dependencies are installed.
    """

    def search_funds(self, query: str) -> List[FundProfile]:
        akshare = _load_akshare()
        frame = akshare.fund_name_em()
        normalized = query.strip().lower()
        if normalized:
            matches = frame[
                frame.astype(str).apply(
                    lambda row: normalized in "".join(row.values.tolist()).lower(),
                    axis=1,
                )
            ].head(20)
        else:
            matches = frame.head(20)
        return [self._profile_from_name_row(row) for _, row in matches.iterrows()]

    def list_funds(self, limit: int = 100) -> List[FundProfile]:
        akshare = _load_akshare()
        frame = akshare.fund_name_em()
        return [self._profile_from_name_row(row) for _, row in frame.head(limit).iterrows()]

    def get_profile(self, code: str) -> FundProfile:
        profile = self._profile_from_xueqiu(code)
        realtime = self._realtime_row(code)
        purchase = self._purchase_row(code)
        if realtime is not None:
            profile = _merge_profile(
                profile,
                purchase_status=_safe_str(realtime.get("申购状态")) or profile.purchase_status,
                redeem_status=_safe_str(realtime.get("赎回状态")) or profile.redeem_status,
                fee_note=_safe_str(realtime.get("手续费")) or profile.fee_note,
            )
        if purchase is not None:
            profile = _merge_profile(
                profile,
                fund_type=_safe_str(purchase.get("基金类型")) or profile.fund_type,
                purchase_status=_safe_str(purchase.get("申购状态")) or profile.purchase_status,
                redeem_status=_safe_str(purchase.get("赎回状态")) or profile.redeem_status,
                fee_note=_safe_str(purchase.get("手续费")) or profile.fee_note,
            )
        return profile

    def get_nav_history(self, code: str) -> List[NavPoint]:
        akshare = _load_akshare()
        unit_frame = akshare.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        accumulated_frame = akshare.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
        if unit_frame.empty:
            raise LookupError("未找到基金净值")

        accumulated_by_date = {}
        if not accumulated_frame.empty:
            for _, row in accumulated_frame.iterrows():
                accumulated_by_date[_safe_str(row.get("净值日期"))] = _safe_float(row.get("累计净值"))

        points: List[NavPoint] = []
        for _, row in unit_frame.iterrows():
            date_value = _safe_str(row.get("净值日期") or row.get("日期"))
            unit_nav = _safe_float(row.get("单位净值"))
            if not date_value or unit_nav is None:
                continue
            accumulated_nav = accumulated_by_date.get(date_value) or unit_nav
            points.append(NavPoint(date=date_value, unit_nav=unit_nav, accumulated_nav=accumulated_nav))
        if not points:
            raise LookupError("未找到可用基金净值")
        return points

    def get_holdings(self, code: str) -> List[FundHolding]:
        akshare = _load_akshare()
        frame = _first_successful_year_call(
            lambda year: akshare.fund_portfolio_hold_em(symbol=code, date=year)
        )
        if frame is None or frame.empty:
            return []
        latest_period = _latest_period(frame, "季度")
        if latest_period:
            frame = frame[frame["季度"].astype(str) == latest_period]
        holdings: List[FundHolding] = []
        for _, row in frame.head(20).iterrows():
            holdings.append(
                FundHolding(
                    stock_code=_safe_str(row.get("股票代码")),
                    stock_name=_safe_str(row.get("股票名称")),
                    ratio=_safe_float(row.get("占净值比例")),
                    shares=_safe_float(row.get("持股数")),
                    market_value=_safe_float(row.get("持仓市值")),
                    period=_safe_str(row.get("季度")),
                )
            )
        return holdings

    def get_industry_allocation(self, code: str) -> List[IndustryAllocation]:
        akshare = _load_akshare()
        frame = _first_successful_year_call(
            lambda year: akshare.fund_portfolio_industry_allocation_em(symbol=code, date=year)
        )
        if frame is None or frame.empty:
            return []
        latest_date = _latest_date(frame, "截止时间")
        if latest_date:
            frame = frame[frame["截止时间"].astype(str) == latest_date]
        allocations: List[IndustryAllocation] = []
        for _, row in frame.head(12).iterrows():
            allocations.append(
                IndustryAllocation(
                    industry=_safe_str(row.get("行业类别")),
                    ratio=_safe_float(row.get("占净值比例")),
                    market_value=_safe_float(row.get("市值")),
                    report_date=_safe_str(row.get("截止时间")),
                )
            )
        return allocations

    def get_fees(self, code: str) -> List[FundFee]:
        akshare = _load_akshare()
        fees: List[FundFee] = []
        try:
            frame = akshare.fund_individual_detail_info_xq(symbol=code)
            for _, row in frame.iterrows():
                fees.append(
                    FundFee(
                        category=_safe_str(row.get("费用类型")),
                        condition=_safe_str(row.get("条件或名称")),
                        value=_safe_str(row.get("费用")),
                    )
                )
        except Exception:
            pass

        for indicator in ["交易状态", "申购与赎回金额", "交易确认日", "运作费用", "赎回费率"]:
            try:
                frame = akshare.fund_fee_em(symbol=code, indicator=indicator)
            except Exception:
                continue
            fees.extend(_fees_from_table(indicator, frame))

        deduped: Dict[str, FundFee] = {}
        for fee in fees:
            key = "%s:%s:%s" % (fee.category, fee.condition, fee.value)
            if fee.category and fee.condition:
                deduped[key] = fee
        return list(deduped.values())[:30]

    def _profile_from_xueqiu(self, code: str) -> FundProfile:
        akshare = _load_akshare()
        try:
            frame = akshare.fund_individual_basic_info_xq(symbol=code)
        except Exception:
            return self._profile_from_name_lookup(code)
        if frame.empty:
            return self._profile_from_name_lookup(code)
        values = {
            _safe_str(row.get("item")): _safe_str(row.get("value"))
            for _, row in frame.iterrows()
        }
        return FundProfile(
            code=values.get("基金代码") or code,
            name=values.get("基金名称") or values.get("基金全称") or code,
            fund_type=values.get("基金类型") or "未知",
            inception_date=values.get("成立时间") or "待补充",
            manager=values.get("基金经理") or "待补充",
            company=values.get("基金公司") or "待补充",
            scale=values.get("最新规模") or "待补充",
            purchase_status="待确认",
            redeem_status="待确认",
            fee_note="费率以基金公司公告为准",
            benchmark=values.get("业绩比较基准") or "待补充",
            investment_objective=values.get("投资目标") or "",
            investment_strategy=values.get("投资策略") or "",
            custodian=values.get("托管银行") or "",
            rating=values.get("基金评级") or "",
            data_source="akshare:xueqiu/eastmoney",
        )

    def _profile_from_name_lookup(self, code: str) -> FundProfile:
        akshare = _load_akshare()
        frame = akshare.fund_name_em()
        row = frame[frame["基金代码"].astype(str) == code]
        if row.empty:
            raise LookupError("未找到基金档案")
        return self._profile_from_name_row(row.iloc[0])

    def _profile_from_name_row(self, row: object) -> FundProfile:
        return FundProfile(
            code=_safe_str(row.get("基金代码")),
            name=_safe_str(row.get("基金简称")),
            fund_type=_safe_str(row.get("基金类型")) or "未知",
            inception_date="待补充",
            manager="待补充",
            company="待补充",
            scale="待补充",
            purchase_status="待确认",
            redeem_status="待确认",
            fee_note="费率以基金公司公告为准",
            benchmark="待补充",
            data_source="akshare:fund_name_em",
        )

    def _realtime_row(self, code: str) -> Optional[object]:
        try:
            frame = _load_akshare().fund_open_fund_daily_em()
            row = frame[frame["基金代码"].astype(str) == code]
            if not row.empty:
                return row.iloc[0]
        except Exception:
            return None
        return None

    def _purchase_row(self, code: str) -> Optional[object]:
        try:
            frame = _load_akshare().fund_purchase_em()
            row = frame[frame["基金代码"].astype(str) == code]
            if not row.empty:
                return row.iloc[0]
        except Exception:
            return None
        return None


def _load_akshare():
    try:
        import akshare  # type: ignore
    except ImportError as exc:
        raise RuntimeError("AKShare 未安装，请先运行 pip install -r requirements.txt") from exc
    return akshare


def _merge_profile(profile: FundProfile, **updates: str) -> FundProfile:
    payload = profile.to_dict()
    payload.update({key: value for key, value in updates.items() if value})
    return FundProfile(**payload)


def _safe_str(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "nat", "<na>", "none"}:
        return ""
    return text


def _safe_float(value: object) -> Optional[float]:
    text = _safe_str(value)
    if not text:
        return None
    text = text.replace(",", "").replace("%", "")
    try:
        return float(text)
    except ValueError:
        return None


def _first_successful_year_call(call):
    current_year = date.today().year
    for year in range(current_year, current_year - 6, -1):
        try:
            frame = call(str(year))
        except Exception:
            continue
        if frame is not None and not frame.empty:
            return frame
    return None


def _latest_period(frame, column: str) -> str:
    periods = [_safe_str(value) for value in frame[column].dropna().unique()]
    if not periods:
        return ""

    def key(value: str):
        match = re.search(r"(\d{4})年(\d)季度", value)
        if not match:
            return (0, 0)
        return (int(match.group(1)), int(match.group(2)))

    return sorted(periods, key=key)[-1]


def _latest_date(frame, column: str) -> str:
    values = sorted(_safe_str(value) for value in frame[column].dropna().unique())
    return values[-1] if values else ""


def _fees_from_table(category: str, frame) -> List[FundFee]:
    fees: List[FundFee] = []
    if frame is None or frame.empty:
        return fees
    if all(isinstance(column, int) for column in frame.columns):
        for _, row in frame.iterrows():
            values = [_safe_str(row.get(column)) for column in frame.columns]
            for index in range(0, len(values), 2):
                if index + 1 < len(values) and values[index] and values[index + 1]:
                    fees.append(FundFee(category=category, condition=values[index], value=values[index + 1]))
        return fees
    columns = list(frame.columns)
    for _, row in frame.iterrows():
        if len(columns) >= 2:
            fees.append(
                FundFee(
                    category=category,
                    condition=_safe_str(row.get(columns[0])),
                    value=_safe_str(row.get(columns[1])),
                )
            )
    return fees
