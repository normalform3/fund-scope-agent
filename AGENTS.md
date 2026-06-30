# FundScope Agent Maintenance Guide

This file guides Codex and future maintainers working on FundScope Agent.

## Project Goal

FundScope Agent is a fund research and risk analysis assistant. It helps ordinary users understand historical fund performance, volatility, drawdown, and suitability signals.

It is not a fund sales system, trading system, or direct recommendation product.

## Current MVP

Implemented:

- FastAPI backend.
- Vue + ECharts frontend workbench.
- sample and AKShare data providers.
- pre-checkup fund discovery with lightweight risk preference questions.
- AKShare real profile, NAV, holdings, industry allocation, and fee mapping.
- SQLite cache.
- deterministic metric calculator.
- structured fund checkup report.
- compliance phrase scanner and conclusion whitelist.
- Bailian OpenAI-compatible model connection test.
- pytest coverage for metrics, compliance, and report generation.

Not implemented yet:

- real LangGraph node graph.
- online LLM report writer.
- full regulatory suitability questionnaire.
- online LLM preference parser.
- multi-fund comparison.
- holdings/fund manager analysis.
- announcement RAG.
- Memory.
- SSE progress stream.

When documenting or changing the project, keep this distinction clear.

## Directory Structure

```text
backend/app/
  api.py                         FastAPI routes
  models.py                      internal DTOs
  agents/                        workflow orchestration
  compliance/                    prohibited wording and report guardrails
  data_providers/                sample and AKShare adapters
  metrics/                       deterministic financial calculations
  reports/                       report assembly and conclusion classification
  services/                      application services and provider/cache coordination
  storage/                       SQLite cache
docs/
  API.md                         API contract and examples
  ARCHITECTURE.md                system design and planned modules
  COMPLIANCE.md                  compliance rules and wording boundaries
  DATA_SOURCES.md                data provider notes and limits
  METRICS.md                     metric definitions and edge cases
  PRD.md                         product requirements
  PROJECT_STATUS.md              current implementation status
  TASKS.md                       milestone checklist
frontend/src/
  App.vue                        main workbench orchestration
  api.ts                         frontend API client and TS types
  components/                    focused Vue workbench sections
  composables/                   frontend progress and chart state helpers
tests/                           backend unit tests
```

## Coding Rules

- Keep changes small and focused.
- Do not mix unrelated backend, frontend, and documentation refactors unless the task requires it.
- Follow existing module boundaries.
- Prefer explicit code over clever abstractions.
- Do not add new production dependencies without a clear reason.
- Do not hardcode secrets, private service URLs, tenant IDs, signed URLs, or account-specific provider endpoints.
- Default provider is `akshare`; `sample` is for fallback, tests, and offline demos.
- Do not write private `DASHSCOPE_BASE_URL` values, workspace IDs, API keys, or account-specific endpoints into repo files.

## Agent Design Principles

- Treat deterministic code as tools.
- Agent workflow may decide order, gather context, explain, ask clarifying questions, and run compliance checks.
- Agent workflow must not calculate financial metrics.
- Each future Agent node must have a clear responsibility, input, output, failure behavior, and termination condition.
- Prefer a simple graph before adding multi-agent complexity.
- Report generation should remain traceable: users should be able to see what data and metrics drove a conclusion.

## LLM vs Deterministic Code

Use deterministic code for:

- returns,
- volatility,
- maximum drawdown,
- Sharpe ratio,
- Calmar ratio,
- win rate,
- ranking calculations,
- validation,
- compliance phrase matching,
- API routing,
- cache reads/writes.

Use LLMs only for:

- intent classification,
- plain-language explanation,
- long document summarization,
- announcement/quarterly report extraction,
- report tone rewriting after metrics are calculated,
- asking clarifying questions.

Every future LLM output must pass through compliance checks before reaching the frontend.

## Financial Compliance Boundary

Never output:

- 必买
- 稳赚
- 保证收益
- 强烈推荐买入
- 未来一定上涨
- 一定会涨
- 无风险
- 保本保收益
- 建议买入
- 建议卖出

Allowed report conclusions:

- 适合关注
- 适合长期观察
- 仅适合高风险用户
- 不适合当前用户
- 数据不足，暂不评价

Every report must include:

```text
仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。
```

If data is missing or unreliable, degrade the report instead of inventing conclusions.

## Documentation Maintenance

After every core behavior change, update the relevant docs in the same task:

- API request/response or endpoint change: update `docs/API.md` and README API summary if user-facing.
- Architecture, module boundary, provider, LangGraph, RAG, Memory, or SSE change: update `docs/ARCHITECTURE.md`.
- Product scope, workflow, target user, or non-goal change: update `docs/PRD.md`.
- Metrics formula or classification threshold change: update `docs/METRICS.md`.
- Compliance wording or allowed conclusion change: update `docs/COMPLIANCE.md` and this file.
- Milestone completion, known issue, or next task change: update `docs/PROJECT_STATUS.md`.
- Setup, demo, screenshot, or interview positioning change: update `README.md`.

If implementation and documentation disagree, code is the source of truth. Update the docs to match the code.

## Verification

Backend:

```bash
source venv/bin/activate
pytest
```

Frontend:

```bash
cd frontend
npm run build
```

API smoke test:

```bash
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/reports/fund-checkup \
  -H "Content-Type: application/json" \
  -d '{"code":"110011"}'
```

Do not claim a feature is complete unless it is implemented and verified.
