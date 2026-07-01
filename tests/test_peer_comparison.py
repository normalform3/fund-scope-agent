from fastapi.testclient import TestClient

from app.api import app
from app.data_providers.sample_provider import SampleFundDataProvider
from app.services.fund_service import FundService
from app.services.peer_comparison_service import PeerComparisonService


class NullCache:
    def get(self, key: str, max_age_seconds: int):
        return None

    def set(self, key: str, payload):
        return None


def _sample_service(provider=None) -> FundService:
    provider = provider or SampleFundDataProvider()
    return FundService(
        provider=provider,
        fallback_provider=provider,
        cache=NullCache(),
    )


def test_peer_comparison_returns_same_category_metrics_and_ranks():
    service = PeerComparisonService(_sample_service())

    result = service.compare("110011", scan_limit=10, max_items=5)

    assert result["target"]["code"] == "110011"
    assert result["category"]["bucket"] == "混合型"
    assert len(result["items"]) >= 2
    assert all("混合" in item["fund_type"] for item in result["items"])
    assert any(item["is_target"] for item in result["items"])
    assert result["ranks"]["max_drawdown"]["count"] == len(result["items"])
    assert result["ranks"]["annualized_volatility"]["direction"] == "lower"
    assert "不构成投资建议" in result["compliance_warnings"][0]
    assert any("同类划分为确定性规则" in note for note in result["data_notes"])


def test_peer_comparison_degrades_when_peer_nav_fails():
    class PartialNavProvider(SampleFundDataProvider):
        def get_nav_history(self, code: str):
            if code == "005827":
                raise LookupError("净值缺失")
            return super().get_nav_history(code)

    service = PeerComparisonService(_sample_service(PartialNavProvider()))

    result = service.compare("110011", scan_limit=10, max_items=5)

    compared_codes = {item["code"] for item in result["items"]}
    assert "110011" in compared_codes
    assert "005827" not in compared_codes
    assert any("005827" in note and "净值数据获取失败" in note for note in result["data_notes"])


def test_peer_comparison_api_shape(monkeypatch):
    monkeypatch.setattr("app.api.peer_comparison_service", PeerComparisonService(_sample_service()))
    client = TestClient(app)

    response = client.get("/api/funds/110011/peer-comparison?scan_limit=10&max_items=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"]["code"] == "110011"
    assert payload["category"]["bucket"] == "混合型"
    assert payload["items"]
    assert "total_return" in payload["items"][0]
    assert "ranks" in payload


def test_watchlist_comparison_dedupes_codes_and_returns_rankings():
    service = PeerComparisonService(_sample_service())

    result = service.compare_codes(["110011", "005827", "110020", "110011"])

    assert result["watchlist"]["codes"] == ["110011", "005827", "110020"]
    assert len(result["items"]) == 3
    assert result["rankings"]["annualized_volatility"]["direction"] == "lower"
    assert len(result["rankings"]["max_drawdown"]["items"]) == 3
    assert any("非持久化观察池" in note for note in result["data_notes"])
    assert "不构成投资建议" in result["compliance_warnings"][0]


def test_watchlist_comparison_degrades_when_one_fund_fails():
    class PartialProvider(SampleFundDataProvider):
        def get_nav_history(self, code: str):
            if code == "005827":
                raise LookupError("净值缺失")
            return super().get_nav_history(code)

    service = PeerComparisonService(_sample_service(PartialProvider()))

    result = service.compare_codes(["110011", "005827", "110020"])

    compared_codes = {item["code"] for item in result["items"]}
    assert compared_codes == {"110011", "110020"}
    assert any("005827" in note and "数据获取失败" in note for note in result["data_notes"])


def test_watchlist_comparison_api_shape(monkeypatch):
    monkeypatch.setattr("app.api.peer_comparison_service", PeerComparisonService(_sample_service()))
    client = TestClient(app)

    response = client.post("/api/funds/compare", json={"codes": ["110011", "005827", "110020"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["watchlist"]["codes"] == ["110011", "005827", "110020"]
    assert payload["items"]
    assert "rankings" in payload
    assert "sharpe_ratio" in payload["rankings"]
