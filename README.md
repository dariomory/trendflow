<p align="center">
  <img src="docs/logo.png" alt="Trendflow logo" width="300"/>
</p>

# Trendflow

[![PyPI version](https://img.shields.io/pypi/v/trendflow-py.svg)](https://pypi.org/project/trendflow-py/)

A type-safe Python library for querying, streaming, and exporting Google Trends data

- GitHub: [https://github.com/dariomory/trendflow/](https://github.com/dariomory/trendflow/)
- PyPI package: [https://pypi.org/project/trendflow-py/](https://pypi.org/project/trendflow-py/) (install name `trendflow-py`; import as `trendflow`)
- Created by: **[Dario Mory](https://mory.dev)** | GitHub [https://github.com/dariomory](https://github.com/dariomory) | PyPI [https://pypi.org/user/dariomory/](https://pypi.org/user/dariomory/)
- Free software: MIT License

## Features

- **Type-safe API:** regions, timeframes, resolutions, and export formats use enums instead of raw strings.
- **Rich queries**: interest over time, regional breakdown, live trending searches, and related queries, with dataclass results.
- **Exports**: JSON, CSV, or load results into a pandas `DataFrame`.

## Usage

```python
import trendflow
from trendflow import Region, Timeframe, Resolution, ExportFormat

# Initialize client (optional API config)
tf = trendflow.Client(language="en", timeout=10)

# --- Enums for type safety ---
# Region.US, Region.GB, Region.DE ...
# Timeframe.PAST_DAY, Timeframe.PAST_WEEK, Timeframe.PAST_YEAR, Timeframe.PAST_5_YEARS
# Resolution.COUNTRY, Resolution.REGION, Resolution.CITY

# Fetch interest over time
data = tf.interest_over_time(
    keywords=["Python", "JavaScript", "Rust"],
    timeframe=Timeframe.PAST_YEAR,
    region=Region.US,
)

# Dataclass-backed results
print(data.keywords)        # ["Python", "JavaScript", "Rust"]
print(data.granularity)     # "weekly"
print(data.points)          # list of TrendPoint(date, scores: dict)

# Get regional breakdown (region defaults to Region.US)
regional = tf.interest_by_region(
    keyword="Python",
    resolution=Resolution.COUNTRY,
)

# Trending searches right now
trending = tf.trending_now(region=Region.US)
for item in trending.results:
    print(item.title, item.traffic, item.articles)  # TrendingItem dataclass

# Related queries — returns RelatedResult dataclass
related = tf.related_queries("machine learning")
for query in related.top:
    print(query.term, query.value)    # RelatedQuery(term, value)
for query in related.rising:
    print(query.term, query.breakout) # RelatedQuery(term, breakout%)

# --- Exports ---
data.export(ExportFormat.CSV,  path="trends.csv")
data.export(ExportFormat.JSON, path="trends.json")
data.to_dataframe()  # pandas DataFrame
```

## Feature Parity

Trendflow also ships as a JavaScript/TypeScript library: [`trendflow-js`](https://github.com/dariomory/trendflow-js) ([npm: `trendflow`](https://www.npmjs.com/package/trendflow)).

Current: [`trendflow-py`](https://github.com/dariomory/trendflow) 0.2.0 · [`trendflow`](https://github.com/dariomory/trendflow-js) 0.1.0. Versions are independent; each changelog cross-references the sibling release.

| Feature | Python — [`trendflow-py`](https://pypi.org/project/trendflow-py/) | JS — [`trendflow`](https://www.npmjs.com/package/trendflow) |
|---------|:----------------------------------:|:---------------------------:|
| Interest over time | ✅ | ✅ |
| Interest by region | ✅ | ✅ |
| Trending now | ✅ | ✅ |
| Trending growth % and volume | ✅ | ✅ |
| Trending for any country code | ✅ | ✅ |
| Trending news articles (RSS) | ✅ | ✅ |
| Selectable trending backend | ✅ | ✅ |
| Related queries | ✅ | ✅ |
| Search suggestions | ✅ `suggestions()` | ✅ `suggestions()` |
| Query by topic (entity mid) | ✅ | ✅ |
| CSV / JSON export | ✅ | ✅ |
| Rotating proxy pool | ✅ | ✅ |
| Browser User-Agent by default | ✅ | ✅ |
| Full geo hierarchy | ✅ `geo_list()` | ✅ `geoList()` |
| Overridable RPC ids | ✅ | ✅ |
| pandas DataFrame | ✅ `to_dataframe()` | ❌ N/A |
| Plain-object rows | ❌ N/A | ✅ `toArray()` |
| ESM + CommonJS + types | ❌ N/A | ✅ |
| CLI | ✅ | 🔜 planned |

### Trending now

Google retired the `hottrends/visualize/internal/data` endpoint, along with
`api/dailytrends` and `api/realtimetrends`; all three now return HTTP 404. `trending_now()`
therefore runs on the `batchexecute` RPC that trends.google.com itself uses, which returns
more than the old endpoint did:

```python
trending = tf.trending_now(Region.US)
for item in trending.results:
    print(item.title, item.growth, item.volume, item.traffic)
    # "fifa world cup 2026"  3650  6  "+3,650%"
```

- `growth` is the percentage rise over the window, `volume` a relative search-volume index.
- Any country code works, not a fixed list, and worldwide is now allowed (and the default).
- `articles` is always empty — this endpoint carries no article links.
- No cookie is needed, and the RPC answers on IPs that get a `429` from the widgetdata
  endpoints, so `trending_now()` often works where the other queries do not.

Pass `window=TRENDING_WINDOW_TOP` for the highest-volume searches instead of the
fastest-growing ones. `window` is an undocumented Google parameter; other integers between
4 and 12 also return data over varying recency windows.

### Trending backends: RPC and RSS

Google exposes trending searches two ways. They are not interchangeable, so `backend` lets
you pick:

| | `"rpc"` (`batchexecute`) | `"rss"` (feed) |
|---|---|---|
| items | 50 | 10 |
| payload | ~2 KB JSON | ~21 KB XML |
| growth % and volume | ✅ | ❌ — buckets like `"2000+"` |
| news articles | ❌ | ✅ |
| ``window`` selection | ✅ | ignored by Google |
| worldwide | ✅ | ❌ country only |

```python
rss = tf.trending_now(Region.US, backend="rss")
rss.source  # "rss"
rss.results[0].articles
# [TrendingArticle(title='...', url='https://...', source='Buffalo News', picture='https://...')]
```

`"auto"` (the default) tries the RPC and falls back to the feed. The RPC comes first
deliberately: it returns five times the items with real growth figures, so defaulting to RSS
would quietly degrade results. Reach for `"rss"` when you want the **articles** — that is the
one thing the RPC cannot give you — or as a second opinion if the RPC id ever goes stale.

Note that the feed is not a lighter path despite being a feed, and Google ignores `hours`,
`sort` and `count` on it: it always returns the same 10 entries.

### Topics and search suggestions

Google distinguishes a **search term** (the literal string) from a **topic** (the entity, in
every spelling and language). `suggestions()` finds the topic; every query method already
accepts one — pass the `mid` where you would pass a keyword.

```python
topics = tf.suggestions("artificial intelligence")
# [TopicSuggestion(mid='/m/0mkz', title='Artificial intelligence', type='Professional field')]

data = tf.interest_over_time(
    keywords=[topics[0].mid, "artificial intelligence"],
    timeframe=Timeframe.PAST_YEAR,
    region=Region.US,
)
# {'/m/0mkz': 62, 'artificial intelligence': 1}
```

That gap is the point: the topic scores **62** where the literal phrase scores **1**, because
it aggregates every phrasing and translation people actually search.

`suggestions()` needs no cookie and no proxy — it answers on IPs the widgetdata endpoints
reject with `429`, same as `trending_now()`. `type` disambiguates same-name entities
(`"Nike"` returns both the company and the goddess) and is `None` when Google omits it.

<a id="rate-limits"></a>
### Rate limits

Google Trends aggressively rate-limits datacenter and shared IPs, so `429` is common even on
your first request of the day. Two things matter:

1. **User-Agent.** Google returns `429` to the default agent strings Python HTTP clients
   send, no matter how few requests you have made. This library sends a browser User-Agent
   by default for exactly that reason.
2. **IP reputation.** Once an IP is flagged, every request gets `429` regardless of headers.
   Route through a residential proxy to recover.

### Using a proxy pool

Pass a list of proxy URLs and the client rotates through them automatically, moving to the
next one whenever a query is refused:

```python
import trendflow
from trendflow import Region

tf = trendflow.Client(
    proxies=[
        "http://user:pass@gate.decodo.com:7000",
        "http://user:pass@gate.decodo.com:7000",
    ],
    max_proxy_attempts=3,  # defaults to the pool size, capped at 5
    on_proxy_rotate=lambda attempt, error: print(f"rotated after {attempt}: {error!r}"),
)

trending = tf.trending_now(Region.US)
print(tf.current_proxy)  # the proxy that answered
```

Entries are just URLs, so a pool can mix providers. Repeating one rotating gateway also works: each entry gets its own connection, so it lands on a fresh exit IP.

**Rotation happens per query, not per request — this matters.** Google binds the `NID`
cookie and the widget token to the IP that requested them, so a single query must complete
on one exit IP; sending the follow-up `widgetdata` call from a different IP earns an instant
`429`. The pool pins one proxy for the whole query and advances only on failure, re-seeding
the cookie jar each time. For the same reason, point the pool at **sticky sessions** rather
than per-request rotating endpoints if your provider offers the choice.

Rotation is skipped for errors a different IP cannot fix, such as a `404` or a renamed RPC.

#### Where to get proxies

Residential proxies are what actually clears Google's `429`. Verified against this library:

<p align="center">
  <a href="https://dashboard.decodo.com/register?referral_code=821058adf31e1b797a169971f79daf86fd5ebbbc"><img src="docs/proxies/decodo.svg" alt="Decodo" height="56"/></a>
</p>

| Provider | Notes | Endpoint format |
|----------|-------|-----------------|
| [Decodo](https://dashboard.decodo.com/register?referral_code=821058adf31e1b797a169971f79daf86fd5ebbbc) (formerly Smartproxy) | Cheapest entry tier; pay-as-you-go available. Used to verify this library's live tests. | `http://user:pass@gate.decodo.com:7000` |

Ask for **sticky sessions** when you sign up — per-request rotating endpoints break the
cookie/token binding described above. Note that a shared residential pool can be exhausted
for Google Trends specifically, in which case even a valid proxy returns `429`; that is what
`max_proxy_attempts` is for.

### If Google renames an RPC

The `batchexecute` RPC identifiers are pinned constants; they are not discoverable at
runtime. If Google renames one, calls raise `UnknownRpcError` naming the identifier, and you
can patch it without waiting for a release by passing `rpc_ids` to
`trendflow._trends_http.batchexecute.BatchExecuteClient`.

## Documentation

Documentation is built with [Zensical](https://zensical.org/) and deployed to GitHub Pages.

- **Live site:** [https://dariomory.github.io/trendflow/](https://dariomory.github.io/trendflow/)
- **Preview locally:** `just docs-serve` (serves at [http://localhost:8000](http://localhost:8000))
- **Build:** `just docs-build`

API documentation is auto-generated from docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Docs deploy automatically on push to `master` or `main` via GitHub Actions.

## Development

To set up for local development:

```bash
# Clone your fork
git clone git@github.com:dariomory/trendflow.git
cd trendflow

# Install in editable mode with live updates
uv tool install --editable .
```

This installs the CLI globally but with live updates - any changes you make to the source code are immediately available when you run `trendflow`.

Run tests:

```bash
uv run pytest
```

Run quality checks (format, lint, type check, test):

```bash
just qa
```

## Author

Trendflow was created in 2026 by Dario Mory