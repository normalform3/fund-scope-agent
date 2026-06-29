# Data Sources

## AKShare

Use in development and portfolio demos when explicitly enabled with `FUNDSCOPE_DATA_PROVIDER=akshare`.

The default local provider is `sample` so the MVP remains fast and demoable without live data access.

Planned data:

- open fund daily data,
- fund profile basics,
- NAV history,
- fund scale,
- manager information,
- holdings and allocation data in later versions.

Limitations:

- Interfaces may change.
- Data refresh timing is not guaranteed by this project.
- AKShare usage is for academic research and learning, not commercial operation.

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

This cache is a local development cache, not a licensed data store. Cached data may include sample or AKShare responses depending on the active provider.

## Commercialization Requirement

Before commercial use:

- replace non-commercial data feeds,
- document licensing,
- add audit logs,
- add data freshness indicators,
- review all public-facing disclaimers with qualified legal/compliance professionals.
