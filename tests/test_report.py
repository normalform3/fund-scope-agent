from app.reports.generator import generate_fund_checkup_report
from app.data_providers.sample_provider import SampleFundDataProvider


def test_generate_report_contains_required_sections():
    provider = SampleFundDataProvider()
    profile = provider.get_profile("110011")
    nav = provider.get_nav_history("110011")

    report = generate_fund_checkup_report(profile, nav)

    assert report["fund"]["code"] == "110011"
    assert report["conclusion"] in {
        "适合关注",
        "适合长期观察",
        "仅适合高风险用户",
        "不适合当前用户",
        "数据不足，暂不评价",
    }
    assert report["metrics"]["max_drawdown"] is not None
    assert report["compliance_warnings"]

