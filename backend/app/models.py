from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FundProfile:
    code: str
    name: str
    fund_type: str
    inception_date: str
    manager: str
    company: str
    scale: str
    purchase_status: str
    redeem_status: str
    fee_note: str
    benchmark: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class NavPoint:
    date: str
    unit_nav: float
    accumulated_nav: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class DrawdownPoint:
    date: str
    drawdown: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class RiskMetrics:
    observation_days: int
    total_return: Optional[float]
    annualized_return: Optional[float]
    annualized_volatility: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    calmar_ratio: Optional[float]
    win_rate: Optional[float]
    max_drawdown_start: Optional[str]
    max_drawdown_trough: Optional[str]
    drawdown_recovery_days: Optional[int]
    period_returns: Dict[str, Optional[float]]
    drawdown_series: List[DrawdownPoint]
    warnings: List[str]

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["drawdown_series"] = [point.to_dict() for point in self.drawdown_series]
        return payload

