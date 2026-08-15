"""
Trending-search backends behind a single interface, so callers need not care which source
answered.

Google exposes trending searches two ways, and they are not interchangeable:

==================  ======================  =============================
\\                   RPC (``batchexecute``)  RSS feed
==================  ======================  =============================
items               50                      10
payload             ~2 KB JSON              ~21 KB XML
growth % / volume   yes                     no -- buckets like ``"2000+"``
news articles       no                      yes
window selection    yes                     ignored by Google
staleness risk      pinned RPC id           stable URL
==================  ======================  =============================

``"auto"`` therefore prefers the RPC and falls back to RSS: the RPC returns five times the
items with real growth figures, so defaulting to RSS would silently degrade results. Choose
``"rss"`` explicitly when you want the articles.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from trendflow import _parsers
from trendflow._trends_http.batchexecute import BatchExecuteClient
from trendflow._trends_http.rss import TrendingRssClient
from trendflow.models import TrendingArticle, TrendingItem

#: How ``trending_now`` picks a source.
TrendingBackend = Literal["auto", "rpc", "rss"]


@runtime_checkable
class TrendingProvider(Protocol):
    """A source of trending searches."""

    @property
    def source(self) -> str: ...

    def fetch(self, geo: str, window: int) -> list[TrendingItem]: ...


class RpcTrendingProvider:
    """The ``batchexecute`` RPC: more items, growth and volume, no articles."""

    source = "rpc"

    def __init__(self, rpc: BatchExecuteClient) -> None:
        self._rpc = rpc

    def fetch(self, geo: str, window: int) -> list[TrendingItem]:
        return _parsers.trending_rows_to_items(self._rpc.trending_searches(geo, window))


class RssTrendingProvider:
    """The RSS feed: fewer items and no growth figures, but carries the news articles."""

    source = "rss"

    def __init__(self, rss: TrendingRssClient) -> None:
        self._rss = rss

    def fetch(self, geo: str, window: int) -> list[TrendingItem]:  # noqa: ARG002 - feed ignores window
        # The feed takes a bare country code and has no worldwide equivalent.
        items = self._rss.trending("" if geo == "Worldwide" else geo)
        return [
            TrendingItem(
                title=item.title,
                traffic=item.approx_traffic or "",
                articles=[
                    TrendingArticle(
                        title=news.title,
                        url=news.url,
                        source=news.source,
                        picture=news.picture,
                    )
                    for news in item.news
                ],
                growth=None,
                volume=None,
                started_at=item.pub_date,
            )
            for item in items
        ]
