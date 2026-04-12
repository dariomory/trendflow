<p align="center">
  <img src="logo.png" alt="Trendflow logo" width="280"/>
</p>

# Trendflow

A type-safe Python library for querying, streaming, and exporting Google Trends data.

The HTTP client returns raw JSON; parsing into dataclasses lives in `trendflow._parsers`, and the high-level [`GoogleTrendsFetcher`](usage.md) (exposed as [`Client`](usage.md)) ties it together. See [Architecture](architecture.md) for the full layout.

## Getting started

- [Installation](installation.md) — how to install Trendflow
- [Architecture](architecture.md) — layers (`_trends_http`, `_parsers`, `_fetcher`, `models`)
- [Usage](usage.md) — how to use Trendflow
- [API Reference](api.md) — auto-generated API documentation
