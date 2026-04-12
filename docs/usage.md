# Usage

## Quick start

```python
import trendflow
from trendflow import Region, Timeframe, Resolution, ExportFormat

# Client is an alias for GoogleTrendsFetcher
tf = trendflow.Client(language="en", timeout=10)

# Interest over time → InterestOverTimeResult (dataclass)
data = tf.interest_over_time(
    keywords=["Python", "JavaScript"],
    timeframe=Timeframe.PAST_YEAR,
    region=Region.US,
)

print(data.keywords, data.granularity, len(data.points))

# Regional breakdown (region defaults to Region.US)
regional = tf.interest_by_region(
    keyword="Python",
    resolution=Resolution.COUNTRY,
)

# Trending searches (requires a country)
trending = tf.trending_now(region=Region.US)
for item in trending.results:
    print(item.title)

# Related queries
related = tf.related_queries("machine learning")
```

## Imports

You can import the same symbols from the package root:

```python
from trendflow import Client, Region, Timeframe, InterestOverTimeResult
```

Or use the fetcher explicitly:

```python
from trendflow import GoogleTrendsFetcher
```

## Low-level session

For raw JSON (no dataclass layer), use `GoogleTrendsHttpSession` from `trendflow._trends_http`: it performs HTTP and returns `dict` / `list` payloads. Parse them yourself or call helpers in `trendflow._parsers`.

## Exports and pandas

`InterestOverTimeResult` supports CSV/JSON export and `to_dataframe()` for a pandas `DataFrame`—see the [API Reference](api.md).
