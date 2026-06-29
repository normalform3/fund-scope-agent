import math
import statistics
from typing import Dict, Iterable, List, Optional, Tuple

from app.models import DrawdownPoint, NavPoint, RiskMetrics

TRADING_DAYS_PER_YEAR = 252
PERIOD_WINDOWS = {
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "1y": 252,
    "3y": 756,
}


def calculate_risk_metrics(
    nav_points: Iterable[NavPoint],
    risk_free_rate: float = 0.02,
) -> RiskMetrics:
    """Calculate reproducible risk metrics from historical NAV data."""
    ordered = sorted(nav_points, key=lambda item: item.date)
    cleaned = [point for point in ordered if point.accumulated_nav > 0]
    warnings: List[str] = []

    if len(cleaned) != len(ordered):
        warnings.append("部分净值数据缺失或非正，已在指标计算中剔除。")

    if len(cleaned) < 2:
        return RiskMetrics(
            observation_days=len(cleaned),
            total_return=None,
            annualized_return=None,
            annualized_volatility=None,
            max_drawdown=None,
            sharpe_ratio=None,
            calmar_ratio=None,
            win_rate=None,
            max_drawdown_start=None,
            max_drawdown_trough=None,
            drawdown_recovery_days=None,
            period_returns={key: None for key in PERIOD_WINDOWS},
            drawdown_series=[],
            warnings=warnings + ["历史净值不足，无法计算可靠风险指标。"],
        )

    values = [point.accumulated_nav for point in cleaned]
    returns = _daily_returns(values)
    total_return = values[-1] / values[0] - 1
    annualized_return = _annualized_return(total_return, len(values))
    annualized_volatility = _annualized_volatility(returns)
    max_dd, dd_start, dd_trough, recovery_days, drawdown_series = _drawdown(cleaned)
    sharpe_ratio = _safe_ratio(annualized_return - risk_free_rate, annualized_volatility)
    calmar_ratio = _safe_ratio(annualized_return, abs(max_dd) if max_dd is not None else None)
    win_rate = _safe_ratio(sum(1 for item in returns if item > 0), len(returns))

    if len(cleaned) < TRADING_DAYS_PER_YEAR:
        warnings.append("历史数据少于一年，年化指标参考价值有限。")

    return RiskMetrics(
        observation_days=len(cleaned),
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe_ratio,
        calmar_ratio=calmar_ratio,
        win_rate=win_rate,
        max_drawdown_start=dd_start,
        max_drawdown_trough=dd_trough,
        drawdown_recovery_days=recovery_days,
        period_returns=_period_returns(values),
        drawdown_series=drawdown_series,
        warnings=warnings,
    )


def _daily_returns(values: List[float]) -> List[float]:
    return [values[index] / values[index - 1] - 1 for index in range(1, len(values))]


def _annualized_return(total_return: float, observations: int) -> Optional[float]:
    if observations < 2:
        return None
    years = (observations - 1) / TRADING_DAYS_PER_YEAR
    if years <= 0:
        return None
    return math.pow(1 + total_return, 1 / years) - 1


def _annualized_volatility(returns: List[float]) -> Optional[float]:
    if len(returns) < 2:
        return None
    return statistics.stdev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR)


def _safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _period_returns(values: List[float]) -> Dict[str, Optional[float]]:
    result: Dict[str, Optional[float]] = {}
    for label, window in PERIOD_WINDOWS.items():
        if len(values) <= window:
            result[label] = None
            continue
        result[label] = values[-1] / values[-1 - window] - 1
    return result


def _drawdown(points: List[NavPoint]) -> Tuple[float, str, str, Optional[int], List[DrawdownPoint]]:
    peak_value = points[0].accumulated_nav
    peak_date = points[0].date
    max_drawdown = 0.0
    max_start = peak_date
    max_trough = peak_date
    trough_index = 0
    start_value = peak_value
    series: List[DrawdownPoint] = []

    for index, point in enumerate(points):
        if point.accumulated_nav > peak_value:
            peak_value = point.accumulated_nav
            peak_date = point.date
        drawdown = point.accumulated_nav / peak_value - 1
        series.append(DrawdownPoint(date=point.date, drawdown=drawdown))
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_start = peak_date
            max_trough = point.date
            trough_index = index
            start_value = peak_value

    recovery_days: Optional[int] = None
    if max_drawdown < 0:
        for index in range(trough_index + 1, len(points)):
            if points[index].accumulated_nav >= start_value:
                recovery_days = index - trough_index
                break

    return max_drawdown, max_start, max_trough, recovery_days, series

