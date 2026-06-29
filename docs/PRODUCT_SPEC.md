# Product Spec

## Positioning

FundScope Agent is a fund research and risk matching assistant for ordinary investors. It helps users understand a fund instead of telling them what to buy.

## V1 Scope

- Search by fund code or name.
- Generate one-fund checkup report.
- Show fund profile, NAV chart, cumulative return chart, drawdown chart.
- Calculate deterministic risk metrics.
- Explain risk notes, suitable users, unsuitable users, and data limitations.
- Enforce compliance wording.

## V1 Non-Goals

- No trade execution.
- No buy/sell instruction.
- No guaranteed return claim.
- No portfolio analysis.
- No investor questionnaire.
- No announcement RAG.
- No commercial data redistribution.

## V2 Scope

- User risk questionnaire.
- Multi-fund comparison.
- Fund manager analysis.
- Style and holding concentration analysis.
- Dollar-cost averaging backtest.

## V3 Scope

- Portfolio risk analysis.
- Holding overlap.
- Announcement and quarterly report RAG.
- Watchlist and risk alerts.

## Main Screen

The first screen is the workbench:

- Left workflow rail.
- Top product header and disclaimer.
- Main fund input area.
- Fund profile strip.
- Metric cards.
- NAV, cumulative return, and drawdown charts.
- Right report panel.

## Report Fields

- `fund`
- `conclusion`
- `summary`
- `metrics`
- `risk_notes`
- `suitable_for`
- `unsuitable_for`
- `data_notes`
- `compliance_warnings`

