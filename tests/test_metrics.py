from app.metrics.calculator import calculate_risk_metrics
from app.models import NavPoint


def test_calculates_max_drawdown_and_total_return():
    points = [
        NavPoint(date="2024-01-01", unit_nav=1.0, accumulated_nav=1.0),
        NavPoint(date="2024-01-02", unit_nav=1.2, accumulated_nav=1.2),
        NavPoint(date="2024-01-03", unit_nav=0.9, accumulated_nav=0.9),
        NavPoint(date="2024-01-04", unit_nav=1.1, accumulated_nav=1.1),
    ]

    metrics = calculate_risk_metrics(points)

    assert round(metrics.total_return, 6) == 0.1
    assert round(metrics.max_drawdown, 6) == -0.25
    assert metrics.max_drawdown_start == "2024-01-02"
    assert metrics.max_drawdown_trough == "2024-01-03"


def test_short_or_empty_history_returns_warning_instead_of_crashing():
    metrics = calculate_risk_metrics([])

    assert metrics.total_return is None
    assert metrics.max_drawdown is None
    assert "历史净值不足" in metrics.warnings[-1]

