# Data Sources

## AKShare

Use in development and portfolio demos. The default provider is now `akshare`.

Set `FUNDSCOPE_DATA_PROVIDER=sample` to force offline demo data.

Planned data:

- open fund daily data,
- fund profile basics,
- NAV history,
- fund scale,
- manager information,
- holdings and allocation data in later versions.
- holdings,
- industry allocation,
- fee and trading rules.

Limitations:

- Interfaces may change.
- Data refresh timing is not guaranteed by this project.
- AKShare usage is for academic research and learning, not commercial operation.

Recorded provider fixtures live under `tests/fixtures/akshare/`. They preserve
known AKShare table shapes for profile, NAV, holdings, industry allocation, and
fee mapping tests. These fixtures verify FundScope's deterministic field
mapping logic, not live AKShare availability, freshness, or licensing status.

## Tushare

Reserved as an optional provider for:

- `fund_basic`,
- `fund_nav`,
- `fund_portfolio`,
- dividends,
- split / adjustment factors.

Limitations:

- Some endpoints require points or account privileges.
- Field names and coverage differ from AKShare.

## Official Disclosure Sources

Later versions can ingest public fund announcements, quarterly reports, semiannual reports, and annual reports from official disclosure platforms.

Use cases:

- fund manager statement summarization,
- holding change explanation,
- risk factor extraction,
- RAG source citations.

## Caching

V1 stores serialized provider responses in SQLite:

- profile TTL: 12 hours,
- NAV TTL: 6 hours.

This cache is a local development cache, not a licensed data store. Cached data may include sample or AKShare responses depending on the active provider. Cache keys include provider namespace.
Report responses expose cache and fallback use through `data_quality.status`.
For example, `cached` means the section came from the local SQLite cache, while
`fallback` means the primary provider failed and the fallback provider returned
usable data. These states are research transparency signals, not guarantees of
freshness or completeness.

## Commercialization Requirement

Before commercial use:

- replace non-commercial data feeds,
- document licensing,
- add audit logs,
- add data freshness indicators,
- review all public-facing disclaimers with qualified legal/compliance professionals.
