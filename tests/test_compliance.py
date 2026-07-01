from app.compliance.checker import ALLOWED_CONCLUSIONS, enforce_report_compliance, scan_text


def test_scan_text_finds_prohibited_phrases():
    assert "稳赚" in scan_text("这只基金稳赚，未来一定上涨")


def test_report_compliance_rewrites_prohibited_phrases_and_limits_conclusion():
    report = {
        "conclusion": "强烈推荐买入",
        "summary": "这只基金稳赚，建议买入。",
        "risk_notes": ["未来一定上涨"],
        "risk_explanation": [
            {
                "title": "亏损压力",
                "explanation": "未来一定上涨",
                "user_meaning": "建议买入。",
            }
        ],
    }

    checked = enforce_report_compliance(report)

    assert checked["conclusion"] in ALLOWED_CONCLUSIONS
    assert not scan_text(str(checked))
    assert checked["risk_explanation"][0]["user_meaning"] == "可纳入观察。"
    assert "仅供研究参考，不构成投资建议" in checked["compliance_warnings"][-1]
