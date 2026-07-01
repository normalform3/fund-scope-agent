from fastapi.testclient import TestClient

from app.agents.fund_checkup_graph import FundCheckupWorkflow
from app.api import app
from app.reports.generator import generate_fund_checkup_report
from app.data_providers.sample_provider import SampleFundDataProvider
from app.services.fund_service import FundService


class NullCache:
    def get(self, key: str, max_age_seconds: int):
        return None

    def set(self, key: str, payload):
        return None


def test_generate_report_contains_required_sections():
    provider = SampleFundDataProvider()
    profile = provider.get_profile("110011")
    nav = provider.get_nav_history("110011")
    holdings = provider.get_holdings("110011")
    industry_allocation = provider.get_industry_allocation("110011")

    report = generate_fund_checkup_report(profile, nav, holdings=holdings, industry_allocation=industry_allocation)

    assert report["fund"]["code"] == "110011"
    assert report["conclusion"] in {
        "适合关注",
        "适合长期观察",
        "仅适合高风险用户",
        "不适合当前用户",
        "数据不足，暂不评价",
    }
    assert report["metrics"]["max_drawdown"] is not None
    assert [item["key"] for item in report["risk_explanation"]] == [
        "loss_pressure",
        "drawdown_journey",
        "volatility_experience",
        "exposure_concentration",
        "holding_risk",
        "risk_adjusted_return",
    ]
    assert all(item["level"] for item in report["risk_explanation"])
    assert any("亏损" in item["user_meaning"] for item in report["risk_explanation"])
    drawdown_journey = next(item for item in report["risk_explanation"] if item["key"] == "drawdown_journey")
    assert "自然日" in drawdown_journey["explanation"]
    assert "未修复回撤" in drawdown_journey["user_meaning"]
    exposure = next(item for item in report["risk_explanation"] if item["key"] == "exposure_concentration")
    assert exposure["metric_label"] == "前十大持仓占比"
    assert exposure["metric_value"] == 0.2752
    assert "前十大持仓合计" in exposure["explanation"]
    assert "第一大行业" in exposure["explanation"]
    quality_by_section = {item["section"]: item for item in report["data_quality"]}
    assert quality_by_section["profile"]["status"] == "success"
    assert quality_by_section["nav_points"]["status"] == "success"
    assert quality_by_section["risk_metrics"]["source"] == "deterministic_metrics"
    assert quality_by_section["holdings"]["item_count"] == len(holdings)
    assert quality_by_section["industry_allocation"]["item_count"] == len(industry_allocation)
    assert report["risk_profile_assessment"]["status"] == "not_provided"
    assert report["compliance_warnings"]


def test_generate_report_assesses_user_risk_profile_without_advice():
    provider = SampleFundDataProvider()
    profile = provider.get_profile("110011")
    nav = provider.get_nav_history("110011")

    report = generate_fund_checkup_report(
        profile,
        nav,
        risk_profile={
            "risk_tolerance": "low",
            "horizon": "short",
            "liquidity_need": "high",
            "max_loss_tolerance": 0.1,
            "investment_horizon_months": 6,
            "can_delay_use": False,
            "money_purpose": "emergency",
        },
    )

    assessment = report["risk_profile_assessment"]
    assert assessment["status"] == "assessed"
    assert assessment["fit_level"] in {"不匹配", "需要谨慎"}
    assert any("可承受阶段性亏损" in reason for reason in assessment["reasons"])
    assert any("预计持有约 6 个月" in reason for reason in assessment["reasons"])
    assert any("不方便延期" in reason for reason in assessment["reasons"])
    assert any("资金用途：应急备用金" in reason for reason in assessment["reasons"])
    assert any("超过" in flag for flag in assessment["risk_flags"])
    assert any("预计持有期限" in flag for flag in assessment["risk_flags"])
    assert any("不方便延期" in flag for flag in assessment["risk_flags"])
    assert any("资金用途偏刚性" in flag for flag in assessment["risk_flags"])
    assert "建议买入" not in str(assessment)


def test_fund_checkup_api_accepts_optional_risk_profile(monkeypatch):
    provider = SampleFundDataProvider()
    service = FundService(provider=provider, fallback_provider=provider, cache=NullCache())
    monkeypatch.setattr("app.api.workflow", FundCheckupWorkflow(service))
    client = TestClient(app)

    response = client.post(
        "/api/reports/fund-checkup",
        json={
            "code": "110011",
            "risk_profile": {
                "risk_tolerance": "low",
                "horizon": "short",
                "liquidity_need": "high",
                "max_loss_tolerance": 0.1,
                "investment_horizon_months": 6,
                "can_delay_use": False,
                "money_purpose": "education",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_profile_assessment"]["status"] == "assessed"
    assert payload["risk_profile_assessment"]["profile"]["risk_tolerance"] == "low"
    assert payload["risk_profile_assessment"]["profile"]["money_purpose"] == "education"
    assert [item["stage"] for item in payload["workflow_trace"]] == [
        "profile",
        "nav_points",
        "holdings",
        "industry_allocation",
        "fees",
        "report_generation",
    ]
    assert all(item["status"] == "success" for item in payload["workflow_trace"])


def test_workflow_trace_records_optional_data_degradation():
    class PartialProvider(SampleFundDataProvider):
        def get_holdings(self, code: str):
            raise LookupError("持仓接口暂不可用")

    provider = PartialProvider()
    service = FundService(provider=provider, fallback_provider=provider, cache=NullCache())
    report = FundCheckupWorkflow(service).run("110011")

    trace_by_stage = {item["stage"]: item for item in report["workflow_trace"]}
    assert report["fund"]["code"] == "110011"
    assert trace_by_stage["profile"]["status"] == "success"
    assert trace_by_stage["nav_points"]["status"] == "success"
    assert trace_by_stage["holdings"]["status"] == "degraded"
    assert trace_by_stage["report_generation"]["status"] == "success"
    quality_by_section = {item["section"]: item for item in report["data_quality"]}
    assert quality_by_section["holdings"]["status"] == "degraded"
    assert quality_by_section["holdings"]["item_count"] == 0
    assert quality_by_section["risk_metrics"]["status"] == "success"
    assert any("holdings" in note and "持仓接口暂不可用" in note for note in report["data_notes"])


def test_data_quality_marks_successful_fallback_source():
    class HoldingsFailingProvider(SampleFundDataProvider):
        def get_holdings(self, code: str):
            raise RuntimeError("主持仓接口超时")

    service = FundService(
        provider=HoldingsFailingProvider(),
        fallback_provider=SampleFundDataProvider(),
        cache=NullCache(),
    )

    report = FundCheckupWorkflow(service).run("110011")

    trace_by_stage = {item["stage"]: item for item in report["workflow_trace"]}
    quality_by_section = {item["section"]: item for item in report["data_quality"]}
    assert trace_by_stage["holdings"]["status"] == "success"
    assert quality_by_section["holdings"]["status"] == "fallback"
    assert quality_by_section["holdings"]["source"] == "sample"
    assert "主数据源失败" in quality_by_section["holdings"]["note"]
    assert quality_by_section["holdings"]["item_count"] > 0
