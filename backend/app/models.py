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
    investment_objective: str = ""
    investment_strategy: str = ""
    custodian: str = ""
    rating: str = ""
    data_source: str = ""

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
class FundHolding:
    stock_code: str
    stock_name: str
    ratio: Optional[float]
    shares: Optional[float]
    market_value: Optional[float]
    period: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IndustryAllocation:
    industry: str
    ratio: Optional[float]
    market_value: Optional[float]
    report_date: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FundFee:
    category: str
    condition: str
    value: str

    def to_dict(self) -> Dict[str, str]:
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


@dataclass(frozen=True)
class InvestorPreferenceProfile:
    investment_goal: str
    horizon: str
    risk_tolerance: str
    liquidity_need: str
    experience_level: str
    preferred_fund_types: List[str]
    notes: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FundTypeMatch:
    fund_type: str
    reason: str
    unsuitable_for: str
    search_keywords: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FundCandidate:
    code: str
    name: str
    fund_type: str
    reason: str
    risk_notes: List[str]
    data_source: str
    next_action: str
    observation_days: int
    annualized_volatility: Optional[float]
    max_drawdown: Optional[float]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
