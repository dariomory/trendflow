"""Tests for the Trending Now RSS backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trendflow._providers import RssTrendingProvider
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError
from trendflow._trends_http.rss import TrendingRssClient, parse_trending_rss

# Shaped exactly like the live feed, including the escaped apostrophe Google emits.
FEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0">
<channel>
<title>Daily Search Trends</title>
<item>
  <title>fluminense vs palmeiras</title>
  <ht:approx_traffic>2000+</ht:approx_traffic>
  <description/>
  <pubDate>Sat, 15 Aug 2026 12:00:00 -0700</pubDate>
  <ht:picture>https://img/one</ht:picture>
  <ht:picture_source>ge</ht:picture_source>
  <ht:news_item>
    <ht:news_item_title>Lei do ex? Palmeiras aposta em Arias com &apos;coringa&apos;</ht:news_item_title>
    <ht:news_item_snippet/>
    <ht:news_item_url>https://uol.com.br/a</ht:news_item_url>
    <ht:news_item_picture>https://img/a</ht:news_item_picture>
    <ht:news_item_source>UOL</ht:news_item_source>
  </ht:news_item>
  <ht:news_item>
    <ht:news_item_title>Fluminense x Palmeiras: onde assistir</ht:news_item_title>
    <ht:news_item_url>https://ge.globo.com/b</ht:news_item_url>
    <ht:news_item_source>ge</ht:news_item_source>
  </ht:news_item>
</item>
<item>
  <title>bare entry</title>
</item>
</channel>
</rss>"""


class TestParseTrendingRss:
    def test_reads_every_item(self) -> None:
        assert len(parse_trending_rss(FEED)) == 2

    def test_reads_title_traffic_and_start(self) -> None:
        item = parse_trending_rss(FEED)[0]
        assert item.title == "fluminense vs palmeiras"
        assert item.approx_traffic == "2000+"
        assert item.pub_date is not None
        assert item.pub_date.isoformat() == "2026-08-15T12:00:00-07:00"
        assert item.picture == "https://img/one"

    def test_reads_news_items_decoding_entities(self) -> None:
        news = parse_trending_rss(FEED)[0].news
        assert len(news) == 2
        assert news[0].title == "Lei do ex? Palmeiras aposta em Arias com 'coringa'"
        assert news[0].url == "https://uol.com.br/a"
        assert news[0].source == "UOL"
        assert news[0].picture == "https://img/a"

    def test_missing_picture_is_none(self) -> None:
        assert parse_trending_rss(FEED)[0].news[1].picture is None

    def test_optional_fields_default_rather_than_raise(self) -> None:
        item = parse_trending_rss(FEED)[1]
        assert item.approx_traffic is None
        assert item.pub_date is None
        assert item.picture is None
        assert item.news == []

    def test_feed_with_no_items(self) -> None:
        assert parse_trending_rss("<rss><channel></channel></rss>") == []

    def test_malformed_xml_returns_empty(self) -> None:
        assert parse_trending_rss("<rss><channel>") == []


def _client(status: int = 200, text: str = FEED) -> tuple[TrendingRssClient, MagicMock]:
    client = TrendingRssClient(timeout=5, headers={})
    response = MagicMock()
    response.status_code = status
    response.text = text
    http = MagicMock()
    http.__enter__.return_value.get.return_value = response
    return client, http


class TestTrendingRssClient:
    def test_requests_the_geo(self) -> None:
        client, http = _client()
        with patch("httpx.Client", return_value=http):
            client.trending("NL")
        assert http.__enter__.return_value.get.call_args.kwargs["params"] == {"geo": "NL"}

    def test_omits_geo_when_blank(self) -> None:
        client, http = _client()
        with patch("httpx.Client", return_value=http):
            client.trending("")
        assert http.__enter__.return_value.get.call_args.kwargs["params"] == {}

    def test_too_many_requests(self) -> None:
        client, http = _client(status=429)
        with patch("httpx.Client", return_value=http), pytest.raises(TooManyRequestsError):
            client.trending("US")

    def test_bad_geo_raises_response_error(self) -> None:
        client, http = _client(status=400)
        with patch("httpx.Client", return_value=http), pytest.raises(ResponseError):
            client.trending("ZZ")


class TestRssTrendingProvider:
    def test_normalizes_into_the_shared_shape(self) -> None:
        rss = MagicMock()
        rss.trending.return_value = parse_trending_rss(FEED)
        items = RssTrendingProvider(rss).fetch("US", 8)

        assert items[0].title == "fluminense vs palmeiras"
        assert items[0].traffic == "2000+"
        assert items[0].growth is None
        assert items[0].volume is None
        assert items[0].started_at is not None
        assert [a.source for a in items[0].articles] == ["UOL", "ge"]

    def test_worldwide_becomes_a_blank_geo(self) -> None:
        rss = MagicMock()
        rss.trending.return_value = []
        RssTrendingProvider(rss).fetch("Worldwide", 8)
        rss.trending.assert_called_once_with("")

    def test_source_label(self) -> None:
        assert RssTrendingProvider(MagicMock()).source == "rss"
