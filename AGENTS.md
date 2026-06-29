# FundScope Agent Development Instructions

## Product Boundary

FundScope Agent is a fund research and risk explanation assistant. It helps users understand fund history, volatility, drawdown, style, and suitability signals.

It must not become a fund sales, trading, or direct recommendation system.

## Deterministic Logic

- Financial metrics must be calculated by code.
- LLMs must not calculate returns, volatility, drawdown, Sharpe ratio, rankings, or portfolio weights.
- LLMs may explain metrics, summarize fund documents, classify user intent, and rewrite reports in plain language.
- Any future LLM output must pass compliance checks before reaching users.

## Compliance Rules

Do not output:

- 必买
- 稳赚
- 保证收益
- 强烈推荐买入
- 未来一定上涨
- 建议买入 / 建议卖出

Allowed conclusions:

- 适合关注
- 适合长期观察
- 仅适合高风险用户
- 不适合当前用户
- 数据不足，暂不评价

Every report must include:

> 仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。

## Architecture Rules

- Keep data providers, metrics, reports, agents, and API routes separate.
- Keep external data adapters behind internal DTOs.
- Handle missing data with warnings or degraded reports instead of fabricated conclusions.
- Add tests when changing metrics, report classification, or compliance behavior.

## Verification

Run the smallest relevant checks:

```bash
source venv/bin/activate
pytest
```

For frontend changes:

```bash
cd frontend
npm run build
```

