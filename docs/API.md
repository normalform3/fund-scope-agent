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

## GET /api/funds/{code}/peer-comparison

Compare a target fund with a limited same-category peer sample. This endpoint
uses deterministic fund-type bucketing and existing risk metrics. It does not
rank funds as buy/sell recommendations. The frontend report view uses this
endpoint after a single-fund checkup to show the fund's same-category position
when peer data can be loaded.

Query parameters:

- `scan_limit`: maximum funds to scan from the provider code table. Defaults to `30`, maximum `100`.
- `max_items`: maximum same-category funds to calculate metrics for. Defaults to `8`, maximum `20`.

Example:

```bash
curl "http://127.0.0.1:8000/api/funds/110011/peer-comparison?scan_limit=30&max_items=8"
```

Response fields:

- `target`: target fund profile.
- `category`: original fund type, normalized peer bucket, and matching rule.
- `items`: target and peer metric rows.
- `ranks`: target fund's rank for total return, annualized return, annualized volatility, maximum drawdown, and Sharpe ratio.
- `data_notes`: scan scope, degradation notes, and current comparison limitations.
- `compliance_warnings`: mandatory disclaimer.

Response shape:

```json
{
  "target": {
    "code": "110011",
    "name": "易方达中小盘混合（示例）",
    "fund_type": "偏股混合型"
  },
  "category": {
    "fund_type": "偏股混合型",
    "bucket": "混合型",
    "matching_rule": "按基金类型归入同类桶后比较，暂不使用 LLM 判断同类。"
  },
  "items": [
    {
      "code": "110011",
      "name": "易方达中小盘混合（示例）",
      "fund_type": "偏股混合型",
      "data_source": "sample",
      "is_target": true,
      "observation_days": 615,
      "total_return": 0.0692,
      "annualized_return": 0.0278,
      "annualized_volatility": 0.0785,
      "max_drawdown": -0.4941,
      "sharpe_ratio": 0.0999,
      "warnings": []
    }
  ],
  "ranks": {
    "max_drawdown": {
      "rank": 2,
      "count": 3,
      "percentile": 0.5,
      "direction": "higher",
      "note": "最大回撤控制在 3 只可比基金中排名第 2，同类样本中处于中间区间。"
    }
  },
  "data_notes": [],
  "compliance_warnings": [
    "仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"
  ]
}
```

## POST /api/funds/compare

Compare a user-supplied, non-persisted watchlist of funds. This endpoint is the
backend foundation for candidate and watchlist comparison; it does not save the
list, and it does not return buy/sell advice. The discovery UI can call this
endpoint after candidate refinement to compare the visible candidates before a
single-fund checkup is generated.

Request:

```json
{
  "codes": ["110011", "005827", "110020"]
}
```

Rules:

- `codes` must contain 2 to 10 values.
- Duplicate or blank codes are ignored after request validation.
- Funds with missing profile or NAV data are skipped and listed in `data_notes`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/funds/compare \
  -H "Content-Type: application/json" \
  -d '{"codes":["110011","005827","110020"]}'
```

Response fields:

- `watchlist`: normalized input codes and persistence note.
- `items`: metric rows for funds that could be loaded and calculated.
- `rankings`: deterministic rankings for total return, annualized return, annualized volatility, maximum drawdown, and Sharpe ratio.
- `data_notes`: skipped funds, sample size notes, and comparison limits.
- `compliance_warnings`: mandatory disclaimer.

Response shape:

```json
{
  "watchlist": {
    "codes": ["110011", "005827", "110020"],
    "persistence": "not_persisted",
    "note": "当前比较基于本次请求中的基金代码，暂不保存为长期观察池。"
  },
  "items": [
    {
      "code": "110011",
      "name": "易方达中小盘混合（示例）",
      "fund_type": "偏股混合型",
      "data_source": "sample",
      "is_target": false,
      "observation_days": 615,
      "total_return": 0.0692,
      "annualized_return": 0.0278,
      "annualized_volatility": 0.0785,
      "max_drawdown": -0.4941,
      "sharpe_ratio": 0.0999,
      "warnings": []
    }
  ],
  "rankings": {
    "annualized_volatility": {
      "direction": "lower",
      "count": 3,
      "items": [
        {
          "rank": 1,
          "code": "110020",
          "name": "易方达沪深300ETF联接（示例）",
          "value": 0.0612
        }
      ]
    }
  },
  "data_notes": [],
  "compliance_warnings": [
    "仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。"
  ]
}
```

## POST /api/reports/fund-checkup

Generate a single-fund checkup report.

Request:

```json
{
  "code": "110011",
  "risk_profile": {
    "risk_tolerance": "low",
    "horizon": "short",
    "liquidity_need": "high",
    "max_loss_tolerance": 0.1,
    "investment_horizon_months": 6,
    "can_delay_use": false,
    "money_purpose": "emergency"
  }
}
```

`risk_profile` is optional. When provided, the backend adds a deterministic
fit explanation based on historical risk metrics. It is not a regulatory
suitability questionnaire and does not produce buy/sell advice.
When a user starts a checkup from a discovery candidate in the frontend, the
discovered risk tolerance, horizon, liquidity need, maximum acceptable loss,
expected holding months, whether the money use can be delayed, and money purpose
are passed as this profile.

Supported `risk_profile` fields:

- `risk_tolerance`: `low`, `medium`, or `high`.
- `horizon`: `short`, `medium`, or `long`.
- `liquidity_need`: `high`, `medium`, or `low`.
- `max_loss_tolerance`: maximum acceptable temporary loss as a decimal, such as `0.1` for 10%.
- `investment_horizon_months`: expected holding horizon in months; the report compares this with historical drawdown recovery pressure.
- `can_delay_use`: optional boolean; `false` means the money is not easy to delay if the fund is still in drawdown near the expected use date.
- `money_purpose`: optional money purpose. Supported values are `emergency`, `education`, `retirement`, `idle`, and `near_term`. The report uses it only for deterministic risk explanation, not buy/sell advice.

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
- `risk_explanation`: structured plain-language explanations of loss pressure, worst drawdown journey, volatility experience, exposure concentration, holding risk, and risk-adjusted return.
- `risk_profile_assessment`: deterministic explanation of how the fund's historical risk metrics fit the optional user risk profile.
- `risk_notes`: major risk explanations.
- `holding_notes`: holding and industry concentration notes.
- `suitable_for`: generic suitable user descriptions.
- `unsuitable_for`: generic unsuitable user descriptions.
- `data_notes`: sample period and missing-data notes.
- `data_quality`: structured data coverage for report sections, including status, item count, source, and note.
- `workflow_trace`: backend stage status for data collection, degradation, and report generation.
- `llm_commentary`: reserved for future model-generated report commentary.
- `compliance_warnings`: mandatory disclaimer and any compliance rewrite notes.

`data_quality.status` values:

- `success`: primary provider returned usable data.
- `fallback`: primary provider failed and the fallback provider returned usable data.
- `cached`: local cache returned usable data.
- `degraded`: optional data section failed and could not be recovered.
- `missing`: no data was available for the section.
- `insufficient`: data exists but is not enough for a reliable calculation.
- `error` or `skipped`: required data failed or the report skipped the section after a required failure.

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
  "risk_explanation": [
    {
      "key": "loss_pressure",
      "title": "亏损压力",
      "level": "高",
      "metric_label": "最大回撤",
      "metric_value": -0.4941,
      "explanation": "样本期最大回撤为 -49.41%，表示从阶段高点到低点的最大净值下跌幅度。",
      "user_meaning": "如果在阶段高点买入，历史上曾经历很深的净值回落，持有者需要较强的亏损承受能力。"
    },
    {
      "key": "drawdown_journey",
      "title": "最难熬区间",
      "level": "高",
      "metric_label": "最大回撤",
      "metric_value": -0.4941,
      "explanation": "样本期最大回撤从 2021-09-17 到 2022-05-24，约 249 个自然日内下跌 -49.41%。",
      "user_meaning": "样本期末尚未识别到回到此前高点，用户需要把这类未修复回撤视为真实持有压力。"
    },
    {
      "key": "exposure_concentration",
      "title": "持仓集中度",
      "level": "中",
      "metric_label": "前十大持仓占比",
      "metric_value": 0.2752,
      "explanation": "最新可得披露中，前十大持仓合计约 27.52%；五粮液（示例）占净值约 9.82%；第一大行业为必需消费品（示例）占净值约 42.00%。",
      "user_meaning": "组合存在一定集中度，需要结合基金类型和历史调仓继续观察。"
    }
  ],
  "risk_profile_assessment": {
    "status": "assessed",
    "fit_level": "不匹配",
    "profile": {
      "risk_tolerance": "low",
      "horizon": "short",
      "liquidity_need": "high",
      "max_loss_tolerance": 0.1,
      "investment_horizon_months": 6,
      "can_delay_use": false,
      "money_purpose": "emergency"
    },
    "reasons": [
      "用户风险偏好：保守；资金期限：短期；流动性需求：高。"
    ],
    "risk_flags": [
      "基金历史最大回撤超过用户填写的可承受阶段性亏损。"
    ]
  },
  "risk_notes": [],
  "holding_notes": [],
  "suitable_for": [],
  "unsuitable_for": [],
  "data_notes": [],
  "data_quality": [
    {
      "section": "nav_points",
      "label": "历史净值",
      "status": "success",
      "item_count": 615,
      "source": "akshare",
      "note": "净值样本区间：2021-01-04 至 2024-01-02。"
    },
    {
      "section": "risk_metrics",
      "label": "风险指标",
      "status": "success",
      "item_count": 615,
      "source": "deterministic_metrics",
      "note": "由历史净值确定性计算，未使用 LLM。"
    },
    {
      "section": "holdings",
      "label": "持仓数据",
      "status": "fallback",
      "item_count": 10,
      "source": "sample",
      "note": "主数据源失败，已使用备用数据源：AKShare 持仓接口暂不可用。"
    }
  ],
  "workflow_trace": [
    {
      "stage": "profile",
      "label": "基金档案",
      "status": "success",
      "message": "已取得基金档案。",
      "item_count": 1
    },
    {
      "stage": "holdings",
      "label": "持仓数据",
      "status": "degraded",
      "message": "持仓接口暂不可用",
      "item_count": 0
    }
  ],
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
    "experience_level": "beginner",
    "max_loss_tolerance": "0.1",
    "investment_horizon_months": "12",
    "can_delay_use": "false",
    "money_purpose": "near_term"
  },
  "include_candidates": false
}
```

Supported answer values:

- `risk_tolerance`: `low`, `medium`, `high`.
- `horizon`: `short`, `medium`, `long`.
- `liquidity_need`: `high`, `medium`, `low`.
- `experience_level`: `beginner`, `some`, `experienced`.
- `max_loss_tolerance`: optional maximum acceptable temporary loss as a decimal string, such as `"0.1"` for 10%.
- `investment_horizon_months`: optional expected holding horizon in months, such as `"6"` or `"36"`.
- `can_delay_use`: optional boolean-like value, such as `"true"` or `"false"`, describing whether the money use can be delayed.
- `money_purpose`: optional purpose value: `emergency`, `education`, `retirement`, `idle`, or `near_term`. Chinese inputs such as `应急`, `教育`, `养老`, and `闲置` are normalized to these values.

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
    "liquidity_need": "high",
    "max_loss_tolerance": "0.1",
    "investment_horizon_months": "6",
    "can_delay_use": "false",
    "money_purpose": "emergency"
  },
  "include_candidates": true,
  "selected_fund_type": "货币型 / 短债型",
  "refinement_text": "希望波动小一点，费用不要太高。"
}
```

Response fields:

- `stage`: `type_match` or `candidate_refinement`.
- `profile`: structured investor preference profile.
- `fund_type_matches`: matched research directions, fit score, reasons, deterministic basis, risk flags, and missing context.
- `candidates`: empty in `type_match`; up to 3 candidate funds in `candidate_refinement`.
- `clarifying_questions`: optional follow-up questions when intent is incomplete.
- `summary`: plain-language discovery result.
- `llm_explanation`: optional LLM-written explanation of the deterministic matching result; falls back to rule text when LLM is unavailable.
- `llm_used`: whether LLM explanation was used in the final payload.
- `decision_basis`: top-level deterministic reasons for the current discovery result.
- `data_notes`: skipped-candidate, degraded-data, or optional LLM-profile parsing notes.
- `compliance_warnings`: mandatory disclaimer and compliance notes.

Implementation notes:

- Risk thresholds, fund type mappings, search keywords, name keywords, seed fund codes, and recall limits are kept in the discovery rules module.
- Candidate recall uses provider search plus provider code-table scanning before applying deterministic NAV, risk, type, and purchase-status filters.
- When `max_loss_tolerance` is provided, candidates whose historical maximum drawdown exceeds that user boundary are excluded with a `data_notes` explanation.
- When `investment_horizon_months` is provided, the discovered profile carries it into candidate checkup so the report can compare expected holding time with historical drawdown recovery pressure.
- When `can_delay_use=false`, the report flags additional pressure if historical drawdown recovery conflicts with the user's expected use date.
- When `money_purpose` is `emergency`, `education`, or `near_term`, the report explains unresolved drawdown or visible volatility as stronger real-world use-date pressure. It does not use purpose to produce buy/sell advice.
- When model credentials are configured, natural language may be parsed into JSON profile hints and deterministic matches may be rewritten into a readable explanation by the text LLM. The LLM does not select, rank, score, calculate metrics, or recommend funds.

Category-first response:

```json
{
  "stage": "type_match",
  "summary": "已根据保守型风险画像推荐基金大类：货币型 / 短债型、债券型。可选择一个方向后继续补充要求，再筛选候选基金。",
  "profile": {
    "risk_tolerance": "low",
    "horizon": "short",
    "liquidity_need": "high",
    "max_loss_tolerance": 0.1,
    "investment_horizon_months": 6,
    "can_delay_use": false,
    "money_purpose": "emergency"
  },
  "fund_type_matches": [
    {
      "fund_type": "货币型 / 短债型",
      "reason": "更重视流动性和低波动，适合作为短期资金的研究起点。",
      "fit_score": 96,
      "basis": ["用户画像偏保守，优先控制净值波动和最大回撤。"],
      "risk_flags": ["不适合追求较高长期收益弹性的用户。"],
      "missing_context": ["可确认这笔钱是否会用于生活、应急或短期支出。"]
    }
  ],
  "candidates": [],
  "llm_explanation": "本次按保守型风险画像、短期资金期限和高流动性需求匹配货币型 / 短债型、债券型。",
  "llm_used": false,
  "decision_basis": ["基金大类由规则模块根据风险、期限、流动性和经验水平匹配，不由 LLM 直接推荐。"]
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
  "max_drawdown": -0.0312,
  "basis": ["债券型 与所选研究方向匹配。", "历史净值样本达到 615 个交易日，满足最小样本要求。"]
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
