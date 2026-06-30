# API Reference

Base URL:

```text
http://127.0.0.1:8000
```

## GET /api/health

Health check.

Response:

```json
{
  "status": "ok",
  "service": "fundscope-agent"
}
```

## GET /api/funds/search

Search funds by code or name.

Query parameters:

- `q`: search text. Empty query returns sample provider entries in sample mode.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/search?q=110011"
```

Response:

```json
{
  "items": [
    {
      "code": "110011",
      "name": "易方达中小盘混合（示例）",
      "fund_type": "偏股混合型",
      "inception_date": "2008-06-19",
      "manager": "示例基金经理",
      "company": "易方达基金（示例）",
      "scale": "约 120 亿元（示例数据）",
      "purchase_status": "开放申购",
      "redeem_status": "开放赎回",
      "fee_note": "费率以基金公司公告为准",
      "benchmark": "沪深300指数收益率 * 70% + 中债指数收益率 * 30%"
    }
  ]
}
```

## GET /api/funds/{code}/profile

Get fund profile.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/profile"
```

Response shape:

```json
{
  "code": "110011",
  "name": "易方达中小盘混合（示例）",
  "fund_type": "偏股混合型",
  "inception_date": "2008-06-19",
  "manager": "示例基金经理",
  "company": "易方达基金（示例）",
  "scale": "约 120 亿元（示例数据）",
  "purchase_status": "开放申购",
  "redeem_status": "开放赎回",
  "fee_note": "费率以基金公司公告为准",
  "benchmark": "沪深300指数收益率 * 70% + 中债指数收益率 * 30%"
}
```

Errors:

- `404`: provider cannot find the fund profile.

## GET /api/funds/{code}/nav

Get historical NAV points.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/nav"
```

Response:

```json
{
  "items": [
    {
      "date": "2021-01-04",
      "unit_nav": 1.0847,
      "accumulated_nav": 1.1715
    }
  ]
}
```

Errors:

- `404`: provider cannot find NAV history.

## GET /api/funds/{code}/holdings

Get latest available stock holdings.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/holdings"
```

Response:

```json
{
  "items": [
    {
      "stock_code": "600519",
      "stock_name": "贵州茅台",
      "ratio": 9.19,
      "shares": 73.0,
      "market_value": 111643.99,
      "period": "2026年1季度股票投资明细"
    }
  ]
}
```

## GET /api/funds/{code}/industry-allocation

Get latest available industry allocation.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/industry-allocation"
```

Response:

```json
{
  "items": [
    {
      "industry": "必需消费品",
      "ratio": 43.77,
      "market_value": 4100000000.0,
      "report_date": "2026-03-31"
    }
  ]
}
```

## GET /api/funds/{code}/fees

Get fee and trading rule rows.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/fees"
```

Response:

```json
{
  "items": [
    {
      "category": "买入规则",
      "condition": "0.0万<买入金额<100.0万",
      "value": "1.50"
    }
  ]
}
```

## POST /api/reports/fund-checkup

Generate a single-fund checkup report.

Request:

```json
{
  "code": "110011"
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/reports/fund-checkup \
  -H "Content-Type: application/json" \
  -d '{"code":"110011"}'
```

Response fields:

- `fund`: fund profile.
- `conclusion`: one of the allowed conclusion labels.
- `summary`: plain-language report summary.
- `metrics`: deterministic metric output.
- `holdings`: latest available holding rows.
- `industry_allocation`: latest available industry allocation rows.
- `fees`: fee and trading rule rows.
- `risk_notes`: major risk explanations.
- `holding_notes`: holding and industry concentration notes.
- `suitable_for`: generic suitable user descriptions.
- `unsuitable_for`: generic unsuitable user descriptions.
- `data_notes`: sample period and missing-data notes.
- `llm_commentary`: reserved for future model-generated report commentary.
- `compliance_warnings`: mandatory disclaimer and any compliance rewrite notes.

Response shape:

```json
{
  "fund": {
    "code": "110011",
    "name": "易方达中小盘混合（示例）"
  },
  "conclusion": "仅适合高风险用户",
  "summary": "该结论只反映历史数据中的风险收益特征，不代表未来表现。",
  "metrics": {
    "observation_days": 615,
    "total_return": 0.0692,
    "annualized_return": 0.0278,
    "annualized_volatility": 0.0785,
    "max_drawdown": -0.4941,
    "sharpe_ratio": 0.0999,
    "calmar_ratio": 0.0563,
    "win_rate": 0.4527,
    "max_drawdown_start": "2021-09-17",
    "max_drawdown_trough": "2022-05-24",
    "drawdown_recovery_days": null,
    "period_returns": {
      "1m": -0.0028,
      "3m": -0.1153,
      "6m": 0.0502,
      "1y": 0.7005,
      "3y": null
    },
    "drawdown_series": [],
    "warnings": []
  },
  "holdings": [],
  "industry_allocation": [],
  "fees": [],
  "risk_notes": [],
  "holding_notes": [],
  "suitable_for": [],
  "unsuitable_for": [],
  "data_notes": [],
  "llm_commentary": "",
  "compliance_warnings": [
    "仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"
  ]
}
```

## POST /api/fund-discovery

Recommend fund categories first, then optionally refine one category into research candidates before running a single-fund checkup. The endpoint returns fund type directions or a candidate watchlist, not buy/sell advice.

Request:

```json
{
  "goal_text": "我是新手，希望稳健一点，一年内可能会用钱。",
  "answers": {
    "risk_tolerance": "low",
    "horizon": "medium",
    "liquidity_need": "medium",
    "experience_level": "beginner"
  },
  "include_candidates": false
}
```

Supported answer values:

- `risk_tolerance`: `low`, `medium`, `high`.
- `horizon`: `short`, `medium`, `long`.
- `liquidity_need`: `high`, `medium`, `low`.
- `experience_level`: `beginner`, `some`, `experienced`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/fund-discovery \
  -H "Content-Type: application/json" \
  -d '{"goal_text":"我是新手，希望稳健一点","answers":{"risk_tolerance":"low","horizon":"short","liquidity_need":"high"},"include_candidates":false}'
```

Refinement request:

```json
{
  "goal_text": "我是新手，希望稳健一点。",
  "answers": {
    "risk_tolerance": "low",
    "horizon": "short",
    "liquidity_need": "high"
  },
  "include_candidates": true,
  "selected_fund_type": "货币型 / 短债型",
  "refinement_text": "希望波动小一点，费用不要太高。"
}
```

Response fields:

- `stage`: `type_match` or `candidate_refinement`.
- `profile`: structured investor preference profile.
- `fund_type_matches`: matched fund categories and reasons.
- `candidates`: empty in `type_match`; up to 3 candidate funds in `candidate_refinement`.
- `clarifying_questions`: optional follow-up questions when intent is incomplete.
- `summary`: plain-language discovery result.
- `data_notes`: skipped-candidate, degraded-data, or optional LLM-profile parsing notes.
- `compliance_warnings`: mandatory disclaimer and compliance notes.

Implementation notes:

- Risk thresholds, fund type mappings, search keywords, name keywords, seed fund codes, and recall limits are kept in the discovery rules module.
- Candidate recall uses provider search plus provider code-table scanning before applying deterministic NAV, risk, type, and purchase-status filters.
- When model credentials are configured, natural language may be parsed into JSON profile hints by the text LLM. The LLM does not select, rank, or recommend funds.

Category-first response:

```json
{
  "stage": "type_match",
  "summary": "已根据保守型风险画像推荐基金大类：货币型 / 短债型、债券型。可选择一个方向后继续补充要求，再筛选候选基金。",
  "fund_type_matches": [
    {
      "fund_type": "货币型 / 短债型",
      "reason": "更重视流动性和低波动，适合作为短期资金的研究起点。"
    }
  ],
  "candidates": []
}
```

Candidate entries in `candidate_refinement` include:

```json
{
  "code": "003376",
  "name": "广发中债7-10年国开债指数（示例）",
  "fund_type": "债券型",
  "reason": "债券型 与当前基金类型方向较匹配，可作为候选观察对象。",
  "risk_notes": ["该候选通过当前保守画像的波动和回撤过滤，但仍需查看底层资产风险。"],
  "data_source": "sample",
  "next_action": "生成体检报告",
  "observation_days": 615,
  "annualized_volatility": 0.0167,
  "max_drawdown": -0.0312
}
```

## GET /api/llm/health

Test Bailian OpenAI-compatible model connectivity.

Required environment variables:

- `DASHSCOPE_API_KEY`
- `DASHSCOPE_BASE_URL`
- `DASHSCOPE_MODEL`, defaults to `qwen3.6-plus`

Example:

```bash
curl "http://127.0.0.1:8000/api/llm/health"
```

Response:

```json
{
  "ok": true,
  "model": "qwen3.6-plus",
  "message": "基金研究 Agent 服务连接正常。",
  "request_id": "...",
  "usage": {}
}
```

## Provider Mode

Default:

```bash
FUNDSCOPE_DATA_PROVIDER=akshare
```

Force offline sample:

```bash
FUNDSCOPE_DATA_PROVIDER=sample
```

Provider mode affects search/profile/NAV/report responses and cache namespace.

## Planned API

Not implemented yet:

- `POST /api/reports/fund-checkup/stream`: SSE progress and final report.
- `POST /api/funds/compare`: multi-fund comparison.
- `POST /api/portfolio/analyze`: portfolio analysis.
- `POST /api/rag/query`: announcement/quarterly report retrieval.
