"""
Google Trends' Trending Now RSS feed.

An independent source for trending searches, on a different host path from the
``batchexecute`` RPC and with no RPC identifier to go stale. Its distinguishing feature is
that every entry carries the news articles behind the trend, which the RPC does not.

It is *not* a lighter path, despite being a feed: it returns 10 items in ~21 KB of XML where
the RPC returns 50 in ~2 KB of JSON, and it reports traffic as coarse buckets (``"2000+"``)
rather than a growth percentage. See :mod:`trendflow._providers` for how the two combine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from trendflow._trends_http.endpoints import HTTP_TOO_MANY_REQUESTS, TRENDING_RSS
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError

#: Namespace Google declares for its Trending Now extensions.
HT_NS = "https://trends.google.com/trending/rss"


@dataclass(frozen=True)
class RssNewsItem:
    """A news article attached to a trending entry."""

    title: str
    url: str
    source: str
    picture: str | None = None


@dataclass(frozen=True)
class RssTrendingItem:
    """One ``<item>`` from the feed."""

    title: str
    #: Google's coarse traffic bucket, e.g. ``"2000+"``. ``None`` when absent.
    approx_traffic: str | None = None
    #: When Google started reporting the trend.
    pub_date: datetime | None = None
    picture: str | None = None
    news: list[RssNewsItem] = field(default_factory=list)


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def parse_trending_rss(xml: str) -> list[RssTrendingItem]:
    """Parse the feed body. Tolerates missing optional fields rather than raising."""
    try:
        root = ElementTree.fromstring(xml)  # noqa: S314 - Google's own feed, not user input
    except ElementTree.ParseError:
        return []

    items: list[RssTrendingItem] = []
    for item in root.iter("item"):
        news = [
            RssNewsItem(
                title=_text(block.find(f"{{{HT_NS}}}news_item_title")) or "",
                url=_text(block.find(f"{{{HT_NS}}}news_item_url")) or "",
                source=_text(block.find(f"{{{HT_NS}}}news_item_source")) or "",
                picture=_text(block.find(f"{{{HT_NS}}}news_item_picture")),
            )
            for block in item.findall(f"{{{HT_NS}}}news_item")
        ]
        items.append(
            RssTrendingItem(
                title=_text(item.find("title")) or "",
                approx_traffic=_text(item.find(f"{{{HT_NS}}}approx_traffic")),
                pub_date=_parse_date(_text(item.find("pubDate"))),
                picture=_text(item.find(f"{{{HT_NS}}}picture")),
                news=news,
            ),
        )
    return items


class TrendingRssClient:
    """Fetches and parses the Trending Now feed."""

    def __init__(
        self,
        timeout: httpx.Timeout | tuple[float, float] | float,
        headers: dict[str, str],
        proxy: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.headers = headers
        self.proxy = proxy

    def trending(self, geo: str) -> list[RssTrendingItem]:
        """
        Trending searches for ``geo``, a country code such as ``"US"``.

        The feed rejects an unknown code with HTTP 400. Google ignores ``hours``, ``sort``
        and ``count`` on this feed -- it always returns the same 10 items -- so no window
        parameter is offered.
        """
        params = {"geo": geo} if geo else {}
        client_kwargs: dict[str, Any] = {"timeout": self.timeout, "headers": self.headers}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        with httpx.Client(**client_kwargs) as client:
            response = client.get(TRENDING_RSS, params=params)

        if response.status_code == HTTP_TOO_MANY_REQUESTS:
            raise TooManyRequestsError.from_response(response)
        if response.status_code != 200:
            raise ResponseError.from_response(response)
        return parse_trending_rss(response.text)
