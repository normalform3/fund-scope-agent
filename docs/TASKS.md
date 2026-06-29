# Tasks

## M0 Project Skeleton

- [x] Backend package and API skeleton.
- [x] Frontend Vue workbench.
- [x] README and project docs.
- [x] Core tests for metrics, compliance, and report generation.
- [x] Initialize Git repository.
- [x] Install dependencies in `venv`.

## M1 Data and Metrics

- [x] Sample offline provider.
- [x] AKShare adapter entrypoint.
- [x] SQLite cache.
- [x] Total return, annualized return, volatility, max drawdown, Sharpe ratio, Calmar ratio, win rate.
- [ ] Validate AKShare field mapping against live API.
- [ ] Add provider integration tests with recorded fixtures.

## M2 Checkup Report API

- [x] `GET /api/health`.
- [x] `GET /api/funds/search`.
- [x] `GET /api/funds/{code}/profile`.
- [x] `GET /api/funds/{code}/nav`.
- [x] `POST /api/reports/fund-checkup`.
- [x] Report compliance enforcement.
- [ ] Expand workflow into explicit LangGraph nodes after baseline is stable.

## M3 Frontend Workbench

- [x] Search/input panel.
- [x] Profile strip.
- [x] Metric cards.
- [x] NAV, return, and drawdown charts.
- [x] Structured report panel.
- [ ] Browser verification after dependencies are installed.
- [ ] Add screenshot to README.

## M4 Portfolio Packaging

- [ ] Add demo script.
- [ ] Add example report JSON.
- [ ] Add resume wording.
- [ ] Add architecture diagram screenshot.
