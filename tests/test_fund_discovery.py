from fastapi.testclient import TestClient

from app.agents.fund_checkup_graph import FundCheckupWorkflow
from app.agents.fund_discovery import FundDiscoveryWorkflow
from app.api import app
from app.compliance.checker import scan_text
from app.data_providers.sample_provider import SampleFundDataProvider
from app.models import NavPoint
from app.services.fund_service import FundService


class NullCache:
    def get(self, key: str, max_age_seconds: int):
        return None

    def set(self, key: str, payload):
        return None


def _sample_workflow() -> FundDiscoveryWorkflow:
    service = FundService(
        provider=SampleFundDataProvider(),
        fallback_provider=SampleFundDataProvider(),
        cache=NullCache(),
    )
    return FundDiscoveryWorkflow(fund_service=service)


class FakeLlmService:
    def __init__(self, payload=None, note=""):
        self.payload = payload or {}
        self.note = note

    def parse_discovery_profile(self, goal_text, answers, refinement_text=""):
        return self.payload, self.note


class FakeExplainingLlmService(FakeLlmService):
    def explain_discovery_decision(self, profile, fund_type_matches, candidates, include_candidates):
        return "这个方向稳赚，建议买入。", ["是否建议买入？"], True, "LLM 解释已生成。"


def test_structured_answers_work_without_natural_language_goal():
    result = _sample_workflow().run(
        "",
        {
            "risk_tolerance": "low",
            "horizon": "short",
            "liquidity_need": "high",
            "experience_level": "beginner",
            "investment_horizon_months": "6",
            "can_delay_use": "false",
            "money_purpose": "应急",
        },
    )

    assert result["profile"]["risk_tolerance"] == "low"
    assert result["profile"]["max_loss_tolerance"] is None
    assert result["profile"]["investment_horizon_months"] == 6
    assert result["profile"]["can_delay_use"] is False
    assert result["profile"]["money_purpose"] == "emergency"
    assert result["fund_type_matches"]
    assert result["stage"] == "type_match"
    assert result["candidates"] == []
    assert result["llm_used"] is False
    assert result["llm_explanation"]
    assert result["decision_basis"]
    assert result["fund_type_matches"][0]["fit_score"] > 0
    assert result["fund_type_matches"][0]["basis"]
    assert result["fund_type_matches"][0]["risk_flags"]


def test_refinement_filters_conservative_profile_without_equity_candidates():
    result = _sample_workflow().run(
        "我是新手，希望稳健一点，半年内可能要用钱",
        {},
        include_candidates=True,
        selected_fund_type="货币型 / 短债型",
        refinement_text="希望波动小一点",
    )

    assert result["candidates"]
    candidate_types = " ".join(candidate["fund_type"] for candidate in result["candidates"])
    assert "偏股" not in candidate_types
    assert "股票" not in candidate_types
    assert "主题" not in candidate_types
    assert all(candidate["basis"] for candidate in result["candidates"])


def test_llm_profile_hints_are_used_before_deterministic_filtering():
    service = FundService(
        provider=SampleFundDataProvider(),
        fallback_provider=SampleFundDataProvider(),
        cache=NullCache(),
    )
    workflow = FundDiscoveryWorkflow(
        fund_service=service,
        llm_service=FakeLlmService(
            {
                "risk_tolerance": "high",
                "horizon": "long",
                "liquidity_need": "low",
                "experience_level": "some",
                "preferred_fund_types": "偏股混合型",
                "max_loss_tolerance": "0.6",
                "investment_horizon_months": "36",
                "can_delay_use": True,
                "money_purpose": "retirement",
                "notes": "LLM 仅解析画像",
            },
            "已使用 LLM 将自然语言偏好解析为结构化画像，候选筛选仍由确定性规则完成。",
        ),
    )

    result = workflow.run(
        "我想长期观察权益类基金",
        {},
        include_candidates=True,
        selected_fund_type="偏股混合型",
        refinement_text="可以接受波动",
    )

    assert result["profile"]["risk_tolerance"] == "high"
    assert result["profile"]["preferred_fund_types"] == ["偏股混合型"]
    assert result["profile"]["max_loss_tolerance"] == 0.6
    assert result["profile"]["investment_horizon_months"] == 36
    assert result["profile"]["can_delay_use"] is True
    assert result["profile"]["money_purpose"] == "retirement"
    assert result["candidates"]
    assert any("LLM" in note for note in result["data_notes"])
    assert all(candidate["observation_days"] >= 120 for candidate in result["candidates"])


def test_candidate_recall_uses_provider_code_table_when_search_is_empty():
    class CodeTableOnlyProvider(SampleFundDataProvider):
        def search_funds(self, query: str):
            return []

        def list_funds(self, limit: int = 100):
            return [self.get_profile("003376")]

    service = FundService(
        provider=CodeTableOnlyProvider(),
        fallback_provider=CodeTableOnlyProvider(),
        cache=NullCache(),
    )

    result = FundDiscoveryWorkflow(fund_service=service).run(
        "稳健债券",
        {"risk_tolerance": "low"},
        include_candidates=True,
        selected_fund_type="债券型",
    )

    assert [candidate["code"] for candidate in result["candidates"]] == ["003376"]


def test_high_risk_profile_can_return_equity_candidates_with_risk_notes():
    result = _sample_workflow().run(
        "我能接受高风险和较大波动，想长期观察权益类基金",
        {"risk_tolerance": "high", "horizon": "long", "liquidity_need": "low"},
        include_candidates=True,
        selected_fund_type="偏股混合型",
        refinement_text="可以接受波动，想看权益类候选",
    )

    assert result["candidates"]
    candidate_types = " ".join(candidate["fund_type"] for candidate in result["candidates"])
    assert "偏股" in candidate_types or "指数" in candidate_types
    assert any(candidate["risk_notes"] for candidate in result["candidates"])


def test_max_loss_tolerance_filters_candidates_beyond_user_boundary():
    result = _sample_workflow().run(
        "我能接受高风险，但最多只能接受5%左右的阶段性亏损",
        {"risk_tolerance": "high", "horizon": "long", "liquidity_need": "low", "max_loss_tolerance": "0.05"},
        include_candidates=True,
        selected_fund_type="偏股混合型",
        refinement_text="想看权益类候选",
    )

    assert result["profile"]["max_loss_tolerance"] == 0.05
    assert result["candidates"] == []
    assert any("最大回撤超过用户可接受" in note for note in result["data_notes"])
    assert any("最大可接受阶段性亏损" in item for item in result["decision_basis"])


def test_insufficient_data_returns_degraded_empty_candidates():
    class InsufficientDataProvider(SampleFundDataProvider):
        def search_funds(self, query: str):
            return [self.get_profile("003376")]

        def get_nav_history(self, code: str):
            return [NavPoint(date="2024-01-01", unit_nav=1.0, accumulated_nav=1.0)]

    service = FundService(
        provider=InsufficientDataProvider(),
        fallback_provider=SampleFundDataProvider(),
        cache=NullCache(),
    )
    result = FundDiscoveryWorkflow(fund_service=service).run(
        "稳健债券",
        {"risk_tolerance": "low"},
        include_candidates=True,
        selected_fund_type="债券型",
    )

    assert result["candidates"] == []
    assert any("数据源" in note or "样本不足" in note for note in result["data_notes"])


def test_discovery_output_removes_prohibited_phrases():
    result = _sample_workflow().run("我想找稳赚并且建议买入的基金", {})

    assert not scan_text(str(result))
    assert "仅供研究参考，不构成投资建议" in result["compliance_warnings"][-1]


def test_llm_explanation_is_sanitized_and_does_not_control_rules():
    service = FundService(
        provider=SampleFundDataProvider(),
        fallback_provider=SampleFundDataProvider(),
        cache=NullCache(),
    )
    workflow = FundDiscoveryWorkflow(fund_service=service, llm_service=FakeExplainingLlmService())

    result = workflow.run(
        "我是新手，希望稳健一点",
        {"risk_tolerance": "low", "horizon": "short", "liquidity_need": "high"},
    )

    assert result["llm_used"] is True
    assert "可纳入观察" in result["llm_explanation"]
    assert not scan_text(str(result))
    assert all(match["fund_type"] != "偏股混合型" for match in result["fund_type_matches"])


def test_fund_discovery_api_shape_and_candidate_checkup(monkeypatch):
    workflow = _sample_workflow()
    monkeypatch.setattr("app.api.discovery_workflow", workflow)
    monkeypatch.setattr("app.api.workflow", FundCheckupWorkflow(workflow.fund_service))

    client = TestClient(app)
    response = client.post(
        "/api/fund-discovery",
        json={
            "goal_text": "我是新手，想先稳健观察",
            "answers": {"risk_tolerance": "low", "horizon": "short", "liquidity_need": "high"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]
    assert payload["fund_type_matches"]
    assert payload["stage"] == "type_match"
    assert payload["candidates"] == []
    assert payload["decision_basis"]
    assert "fit_score" in payload["fund_type_matches"][0]
    assert "basis" in payload["fund_type_matches"][0]
    assert "llm_explanation" in payload

    refine_response = client.post(
        "/api/fund-discovery",
        json={
            "goal_text": "我是新手，想先稳健观察",
            "answers": {"risk_tolerance": "low", "horizon": "short", "liquidity_need": "high"},
            "include_candidates": True,
            "selected_fund_type": payload["fund_type_matches"][0]["fund_type"],
            "refinement_text": "希望波动小一点",
        },
    )
    assert refine_response.status_code == 200
    refined = refine_response.json()
    assert refined["stage"] == "candidate_refinement"
    assert refined["candidates"]
    assert refined["candidates"][0]["basis"]

    code = refined["candidates"][0]["code"]
    report_response = client.post("/api/reports/fund-checkup", json={"code": code})
    assert report_response.status_code == 200
    assert report_response.json()["fund"]["code"] == code
