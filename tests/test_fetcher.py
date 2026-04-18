"""Tests for trendflow._fetcher (GoogleTrendsFetcher and helpers)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trendflow._fetcher import (
    TRENDING_PN,
    GoogleTrendsFetcher,
    TrendsFetcher,
    _hl_from_language,
)
from trendflow.enums import Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedResult,
    TrendingResult,
)


class TestHlFromLanguage:
    def test_language_without_dash_appends_us(self) -> None:
        assert _hl_from_language("en") == "en-US"

    def test_language_with_dash_returned_as_is(self) -> None:
        assert _hl_from_language("en-GB") == "en-GB"

    def test_two_char_language_gets_us_suffix(self) -> None:
        assert _hl_from_language("fr") == "fr-US"

    def test_already_full_locale_unchanged(self) -> None:
        assert _hl_from_language("zh-CN") == "zh-CN"


class TestTrendingPnMapping:
    def test_us_maps_to_united_states(self) -> None:
        assert TRENDING_PN[Region.US] == "united_states"

    def test_gb_maps_to_united_kingdom(self) -> None:
        assert TRENDING_PN[Region.GB] == "united_kingdom"

    def test_worldwide_not_in_mapping(self) -> None:
        assert Region.WORLDWIDE not in TRENDING_PN

    def test_all_non_worldwide_regions_have_mapping(self) -> None:
        for region in Region:
            if region is not Region.WORLDWIDE:
                assert region in TRENDING_PN, f"Missing TRENDING_PN entry for {region!r}"


def _make_fetcher() -> GoogleTrendsFetcher:
    """Build a GoogleTrendsFetcher with GoogleTrendsHttpSession patched out."""
    with patch("trendflow._fetcher.GoogleTrendsHttpSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.geo = "US"
        mock_session_cls.return_value = mock_session
        fetcher = GoogleTrendsFetcher()
    return fetcher


class TestGoogleTrendsFetcherInit:
    def test_default_language_passed_as_hl(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession") as mock_cls:
            mock_cls.return_value = MagicMock(geo="")
            GoogleTrendsFetcher(language="en")
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["hl"] == "en-US"

    def test_hyphenated_language_passed_unchanged(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession") as mock_cls:
            mock_cls.return_value = MagicMock(geo="")
            GoogleTrendsFetcher(language="en-GB")
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["hl"] == "en-GB"

    def test_timeout_tuple_uses_doubled_read(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession") as mock_cls:
            mock_cls.return_value = MagicMock(geo="")
            GoogleTrendsFetcher(timeout=10)
        call_kwargs = mock_cls.call_args.kwargs
        connect, read = call_kwargs["timeout"]
        assert connect == 10
        assert read == max(20, 15)  # max(timeout*2, timeout+5) = max(20, 15) = 20

    def test_timeout_min_read_is_timeout_plus_5(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession") as mock_cls:
            mock_cls.return_value = MagicMock(geo="")
            GoogleTrendsFetcher(timeout=3)
        call_kwargs = mock_cls.call_args.kwargs
        connect, read = call_kwargs["timeout"]
        assert connect == 3
        assert read == max(6, 8)  # max(3*2, 3+5) = max(6, 8) = 8


class TestTrendsFetcherProtocol:
    def test_google_trends_fetcher_implements_protocol(self) -> None:
        fetcher = _make_fetcher()
        assert isinstance(fetcher, TrendsFetcher)

    def test_protocol_methods_exist(self) -> None:
        fetcher = _make_fetcher()
        assert hasattr(fetcher, "interest_over_time")
        assert hasattr(fetcher, "interest_by_region")
        assert hasattr(fetcher, "trending_now")
        assert hasattr(fetcher, "related_queries")


class TestInterestOverTime:
    def test_calls_build_payload_with_correct_args(self) -> None:
        fetcher = _make_fetcher()
        mock_default = {"timelineData": []}
        fetcher._req.interest_over_time.return_value = mock_default
        fetcher._req.geo = "US"

        fetcher.interest_over_time(
            keywords=["Python"],
            timeframe=Timeframe.PAST_YEAR,
            region=Region.US,
        )

        fetcher._req.build_payload.assert_called_once_with(
            ["Python"],
            cat=0,
            timeframe=Timeframe.PAST_YEAR.value,
            geo=Region.US.value,
            gprop="",
        )

    def test_returns_interest_over_time_result(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.interest_over_time.return_value = {"timelineData": []}
        fetcher._req.geo = "US"

        result = fetcher.interest_over_time(
            keywords=["Python"],
            timeframe=Timeframe.PAST_YEAR,
            region=Region.US,
        )

        assert isinstance(result, InterestOverTimeResult)

    def test_passes_geo_from_session(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.interest_over_time.return_value = {"timelineData": []}
        fetcher._req.geo = ["US"]

        result = fetcher.interest_over_time(
            keywords=["Python"],
            timeframe=Timeframe.PAST_YEAR,
            region=Region.US,
        )

        assert result.keywords == ["Python"]


class TestInterestByRegion:
    def test_returns_empty_result_when_no_geo_map_data(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.interest_by_region.return_value = {}

        result = fetcher.interest_by_region(
            keyword="Python",
            resolution=Resolution.COUNTRY,
            region=Region.US,
        )

        assert isinstance(result, InterestByRegionResult)
        assert result.rows == []
        assert result.keyword == "Python"

    def test_calls_build_payload_with_keyword(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.interest_by_region.return_value = {}

        fetcher.interest_by_region(keyword="Rust", resolution=Resolution.REGION, region=Region.US)

        fetcher._req.build_payload.assert_called_once_with(
            ["Rust"],
            cat=0,
            timeframe=Timeframe.PAST_YEAR.value,
            geo=Region.US.value,
            gprop="",
        )

    def test_returns_parsed_result_when_data_present(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.interest_by_region.return_value = {
            "geoMapData": [{"geoName": "California", "value": "[90]"}]
        }

        result = fetcher.interest_by_region(
            keyword="Python", resolution=Resolution.REGION, region=Region.US
        )

        assert isinstance(result, InterestByRegionResult)
        assert len(result.rows) == 1
        assert result.rows[0].label == "California"


class TestTrendingNow:
    def test_worldwide_raises_value_error(self) -> None:
        fetcher = _make_fetcher()
        with pytest.raises(ValueError, match="specific country"):
            fetcher.trending_now(region=Region.WORLDWIDE)

    def test_valid_region_calls_trending_searches(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.trending_searches.return_value = ["AI", "Python"]

        result = fetcher.trending_now(region=Region.US)

        fetcher._req.trending_searches.assert_called_once_with(pn="united_states")
        assert isinstance(result, TrendingResult)

    def test_returns_correct_titles(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.trending_searches.return_value = ["AI tools", "Python 4"]

        result = fetcher.trending_now(region=Region.US)

        assert result.results[0].title == "AI tools"
        assert result.results[1].title == "Python 4"

    def test_pn_lookup_for_gb(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.trending_searches.return_value = []

        fetcher.trending_now(region=Region.GB)

        fetcher._req.trending_searches.assert_called_once_with(pn="united_kingdom")

    def test_pn_lookup_for_de(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.trending_searches.return_value = []

        fetcher.trending_now(region=Region.DE)

        fetcher._req.trending_searches.assert_called_once_with(pn="germany")


class TestRelatedQueries:
    def test_calls_build_payload_with_keyword(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.related_queries.return_value = {}

        fetcher.related_queries(keyword="Python")

        fetcher._req.build_payload.assert_called_once_with(
            ["Python"],
            cat=0,
            timeframe=Timeframe.PAST_YEAR.value,
            geo="",
            gprop="",
        )

    def test_returns_related_result(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.related_queries.return_value = {
            "Python": {
                "top": [{"query": "python tutorial", "value": 100}],
                "rising": [],
            }
        }

        result = fetcher.related_queries(keyword="Python")

        assert isinstance(result, RelatedResult)
        assert len(result.top) == 1
        assert result.top[0].term == "python tutorial"

    def test_empty_raw_returns_empty_result(self) -> None:
        fetcher = _make_fetcher()
        fetcher._req.related_queries.return_value = {}

        result = fetcher.related_queries(keyword="Python")

        assert result.top == []
        assert result.rising == []
