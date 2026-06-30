# Project Status

Last updated: 2026-06-30

## Current Phase

MVP scaffold complete. The project now defaults to AKShare real data with sample fallback, can find pre-checkup candidate funds, and can generate a single-fund checkup report.

## Completed

Backend:

- FastAPI app created.
- CORS configured for local Vite frontend.
- Health endpoint implemented.
- Fund search/profile/NAV endpoints implemented.
- Fund discovery endpoint implemented at `POST /api/fund-discovery`.
- Single-fund checkup report endpoint implemented.
- `FundService` coordinates provider access and SQLite cache.
- Cache keys include provider namespace.
- sample provider implemented for offline fallback demos.
- AKShare provider implemented as default for fund profile, unit/accumulated NAV, holdings, industry allocation, and fees.
- Bailian OpenAI-compatible connection test implemented at `GET /api/llm/health`.
- Report data collection now fetches profile, NAV, holdings, industry allocation, and fees concurrently.
- Deterministic metric calculator implemented.
- Discovery rules module implemented for risk thresholds, fund type mappings, search keywords, seed codes, and recall limits.
- Deterministic preference-to-fund-type mapping, expanded candidate recall, and candidate filtering implemented.
- Optional LLM JSON profile parsing implemented before deterministic discovery; unavailable or invalid model output degrades to rule parsing.
- Report generator implemented.
- Compliance checker implemented.

Frontend:

- Vue 3 + Vite app created.
- Main workbench orchestrated in `App.vue`.
- Notion-style workspace UI split into focused Vue components.
- Frontend progress and chart state extracted into composables.
- API client and TypeScript types implemented.
- Fund discovery panel implemented before the direct fund-code checkup flow.
- ECharts renders NAV, cumulative return, and drawdown charts.
- Loading, error, empty, report, tab, and metric states implemented.
- Visual progress bar and staged report generation status implemented.
- Left workspace navigation now focuses search or switches report tabs.

Docs:

- README for interview/demo presentation.
- AGENTS maintenance guide.
- PRD.
- Architecture document.
- API reference.
- Metrics document.
- Compliance document.
- Data source notes.
- Task list.
- Project status.

Tests and verification:

- `pytest` passes.
- `npm run build` passes.
- API smoke tests passed for health and report endpoints.
- Frontend local server responds with `200 OK`.

## Not Completed

- Explicit LangGraph node graph.
- Real LLM report writer.
- Full regulatory suitability questionnaire.
- Multi-fund comparison.
- Portfolio analysis.
- Holdings and industry concentration analysis.
- Fund manager attribution.
- Announcement/quarterly report RAG.
- Memory module.
- SSE progress endpoint.
- Screenshot asset under `docs/assets/`.
- Recorded fixtures for AKShare integration tests.

## Known Issues

- `npm install` reports 2 audit issues. `npm audit fix --force` was not run because it may introduce breaking dependency changes.
- Frontend production build warns that the ECharts bundle chunk is larger than 500 kB.
- Python runtime is local Python 3.9.6, while original plan preferred Python 3.11+. Current code is compatible with 3.9.
- `urllib3` emits a LibreSSL warning on the local macOS Python runtime; tests still pass.
- AKShare live calls may be slow or unstable; current MVP falls back to sample on provider failure.
- The report response includes full `drawdown_series`, which can be large for long live histories.
- 百炼模型测试需要 `DASHSCOPE_BASE_URL`；当前本地环境未检测到该变量。
- Current Codex shell can read `DASHSCOPE_API_KEY` but cannot read `DASHSCOPE_BASE_URL`.

## Next Tasks

1. Add `docs/assets/fundscope-workbench.png` screenshot and reference it from README.
2. Add recorded provider fixtures for AKShare field mapping.
3. Configure `DASHSCOPE_BASE_URL` and verify `/api/llm/health` against Bailian.
4. Split `FundCheckupWorkflow` into explicit LangGraph nodes.
5. Add SSE endpoint for report progress.
6. Add fund manager attribution model before implementing manager analysis.
7. Add API tests with FastAPI `TestClient`.
8. Consider dynamic imports or manual chunks for ECharts.

## Recent Changes

2026-06-30:

- Added `FundDiscoveryWorkflow` for pre-checkup candidate selection.
- Added `POST /api/fund-discovery` with structured preference profile, fund type matches, optional candidate refinement, data notes, and compliance warnings.
- Expanded sample provider with money, bond, index, and 偏股混合 demo candidates.
- Split the Vue workspace into separate `寻找基金` and `基金分析` modules in the left navigation.
- Changed discovery UI to recommend fund categories first, then refine candidates after the user adds further requirements.
- Added discovery tests for structured answers, conservative filtering, high-risk candidates, degraded data, compliance wording, and API shape.
- Extracted discovery thresholds and fund type mappings into `backend/app/agents/discovery_rules.py`.
- Expanded candidate recall with search keywords, name keywords, seed fund codes, and provider code-table scanning.
- Added optional LLM JSON profile parsing while keeping matching, metrics, filtering, and compliance deterministic.
- Updated README, API, architecture, PRD, compliance, task, and status docs for the new candidate workflow.

2026-06-29:

- Refactored the Vue frontend into a Notion-style research workspace.
- Split the former single-file workbench into focused components and composables.
- Preserved the existing backend API contract, report flow, ECharts views, progress states, and model health test.
- Added visual progress bar and staged generation messages for slow AKShare report generation.
- Made left rail menu buttons interactive.
- Parallelized report data collection in the workflow.
- Fixed frontend crash when a degraded report response lacks expected fields.
- Standardized workflow error responses to keep the report JSON shape stable.
- Expanded AKShare provider to real profile, unit/accumulated NAV, holdings, industry allocation, and fees.
- Added Bailian model connection test service and frontend button.
- Added report fields for holdings, industry allocation, fees, and holding notes.
- Created documentation system requested by the user.
- Expanded README for interview presentation.
- Rewrote AGENTS maintenance guide.
- Added PRD.
- Expanded architecture document with Provider, LangGraph, RAG, Memory, and SSE design.
- Added API reference.
- Added project status tracking.

Earlier 2026-06-29:

- Scaffolded backend, frontend, tests, docs, `venv`, and Git repository.
- Implemented sample provider, AKShare provider, SQLite cache, metric calculator, report generator, compliance checker, API routes, and Vue workbench.

## Documentation Maintenance Rule

Whenever core behavior changes:

- update `docs/PROJECT_STATUS.md`,
- update `docs/API.md` for endpoint or response changes,
- update `docs/ARCHITECTURE.md` for module/workflow/provider changes,
- update the most specific related document, such as `docs/METRICS.md`, `docs/COMPLIANCE.md`, or `docs/DATA_SOURCES.md`.

If code and docs disagree, code is the source of truth and docs must be corrected.
