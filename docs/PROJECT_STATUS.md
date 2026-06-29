# Project Status

Last updated: 2026-06-29

## Current Phase

MVP scaffold complete. The project now defaults to AKShare real data with sample fallback and can generate a single-fund checkup report.

## Completed

Backend:

- FastAPI app created.
- CORS configured for local Vite frontend.
- Health endpoint implemented.
- Fund search/profile/NAV endpoints implemented.
- Single-fund checkup report endpoint implemented.
- `FundService` coordinates provider access and SQLite cache.
- Cache keys include provider namespace.
- sample provider implemented for offline fallback demos.
- AKShare provider implemented as default for fund profile, unit/accumulated NAV, holdings, industry allocation, and fees.
- Bailian OpenAI-compatible connection test implemented at `GET /api/llm/health`.
- Report data collection now fetches profile, NAV, holdings, industry allocation, and fees concurrently.
- Deterministic metric calculator implemented.
- Report generator implemented.
- Compliance checker implemented.

Frontend:

- Vue 3 + Vite app created.
- Main workbench implemented in `App.vue`.
- API client and TypeScript types implemented.
- ECharts renders NAV, cumulative return, and drawdown charts.
- Loading, error, empty, report, tab, and metric states implemented.
- Visual progress bar and staged report generation status implemented.
- Left rail actions now focus search or switch report tabs.

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
- User risk profile questionnaire.
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
6. Add user risk questionnaire and suitability mapping.
7. Add fund manager attribution model before implementing manager analysis.
8. Add API tests with FastAPI `TestClient`.
9. Consider dynamic imports or manual chunks for ECharts.

## Recent Changes

2026-06-29:

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
