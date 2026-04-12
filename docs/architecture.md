# Architecture

Trendflow separates **HTTP transport**, **JSON parsing**, and **application-facing fetchers** so each layer has a single responsibility.

## Layers

| Module | Role |
|--------|------|
| `trendflow._trends_http` | Low-level access to Google Trends JSON endpoints. `GoogleTrendsHttpSession` builds explore/widget payloads and returns **raw JSON** (`dict` / `list`). It does **not** depend on pandas. |
| `trendflow._parsers` | Converts that raw JSON into domain dataclasses (`InterestOverTimeResult`, `TrendingResult`, etc.) using the standard library only. |
| `trendflow._fetcher` | `GoogleTrendsFetcher` orchestrates the session plus parsers and implements the `TrendsFetcher` protocol for tests or alternate backends. |
| `trendflow.models` | Dataclasses and optional `InterestOverTimeResult.to_dataframe()` (pandas) for convenience. |

## Pandas

Pandas is used for **user-facing helpers** (for example `InterestOverTimeResult.to_dataframe()` and CSV/JSON export paths), not inside `_trends_http` or `_parsers`.

## Public entry points

Import `Client` (alias for `GoogleTrendsFetcher`) and enums from the top-level `trendflow` package—see [Usage](usage.md).
