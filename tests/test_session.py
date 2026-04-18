"""Tests for trendflow._trends_http.session helper functions and GoogleTrendsHttpSession."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trendflow._trends_http.session import (
    GoogleTrendsHttpSession,
    _normalize_proxies,
    _primary_geo,
)
from trendflow._trends_http.transport import TrendsJsonTransport


def _make_session(**kwargs) -> GoogleTrendsHttpSession:
    """Build a GoogleTrendsHttpSession with the transport patched out."""
    defaults: dict = {"hl": "en-US", "tz": 360}
    defaults.update(kwargs)
    with patch.object(TrendsJsonTransport, "_fetch_nid_cookies", return_value={}):
        session = GoogleTrendsHttpSession(**defaults)
    return session


class TestNormalizeProxies:
    def test_empty_string_returns_empty_list(self) -> None:
        assert _normalize_proxies("") == []

    def test_non_empty_string_returns_single_element_list(self) -> None:
        assert _normalize_proxies("http://proxy:8080") == ["http://proxy:8080"]

    def test_list_of_strings_returned_as_list(self) -> None:
        proxies = ["http://p1:8080", "http://p2:8080"]
        assert _normalize_proxies(proxies) == proxies

    def test_tuple_of_strings_returned_as_list(self) -> None:
        result = _normalize_proxies(("http://p1:8080",))
        assert result == ["http://p1:8080"]

    def test_empty_list_returns_empty_list(self) -> None:
        assert _normalize_proxies([]) == []


class TestPrimaryGeo:
    def test_string_returned_as_is(self) -> None:
        assert _primary_geo("US") == "US"

    def test_empty_string_returned(self) -> None:
        assert _primary_geo("") == ""

    def test_list_returns_first_element(self) -> None:
        assert _primary_geo(["US", "GB"]) == "US"

    def test_empty_list_returns_empty_string(self) -> None:
        assert _primary_geo([]) == ""

    def test_single_element_list(self) -> None:
        assert _primary_geo(["DE"]) == "DE"


class TestGoogleTrendsHttpSessionInit:
    def test_default_attributes(self) -> None:
        session = _make_session()
        assert session.hl == "en-US"
        assert session.tz == 360
        assert session.kw_list == []
        assert session.token_payload == {}

    def test_geo_stored(self) -> None:
        session = _make_session(geo="US")
        assert session.geo == "US"

    def test_proxies_normalized(self) -> None:
        session = _make_session(proxies="http://proxy:8080")
        assert session.proxies == ["http://proxy:8080"]

    def test_empty_proxies(self) -> None:
        session = _make_session(proxies="")
        assert session.proxies == []

    def test_cookies_property(self) -> None:
        session = _make_session()
        session._http.cookies = {"NID": "abc"}
        assert session.cookies == {"NID": "abc"}

    def test_cookies_setter(self) -> None:
        session = _make_session()
        session.cookies = {"NID": "xyz"}
        assert session._http.cookies == {"NID": "xyz"}

    def test_proxy_index_property(self) -> None:
        session = _make_session()
        assert session.proxy_index == 0


class TestBuildPayload:
    def test_invalid_gprop_raises_value_error(self) -> None:
        session = _make_session()
        with pytest.raises(ValueError, match="gprop"):
            with patch.object(session, "_tokens"):
                session.build_payload(["Python"], gprop="invalid")  # type: ignore[arg-type]

    def test_valid_gprop_values(self) -> None:
        session = _make_session()
        for gprop in ("", "images", "news", "youtube", "froogle"):
            with patch.object(session, "_tokens"):
                session.build_payload(["Python"], gprop=gprop)  # type: ignore[arg-type]

    def test_kw_list_stored(self) -> None:
        session = _make_session()
        with patch.object(session, "_tokens"):
            session.build_payload(["Python", "JS"])
        assert session.kw_list == ["Python", "JS"]

    def test_geo_updated_when_provided(self) -> None:
        session = _make_session(geo="")
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"], geo="US")
        assert "US" in session.geo

    def test_geo_preserved_when_not_provided(self) -> None:
        session = _make_session(geo="DE")
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"], geo="")
        assert "DE" in session.geo

    def test_token_payload_has_req_key(self) -> None:
        session = _make_session()
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"])
        assert "req" in session.token_payload

    def test_token_payload_has_hl_and_tz(self) -> None:
        session = _make_session(hl="en-US", tz=360)
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"])
        assert session.token_payload["hl"] == "en-US"
        assert session.token_payload["tz"] == 360

    def test_calls_tokens(self) -> None:
        session = _make_session()
        with patch.object(session, "_tokens") as mock_tokens:
            session.build_payload(["Python"])
        mock_tokens.assert_called_once()

    def test_list_timeframe_builds_per_item_payload(self) -> None:
        session = _make_session()
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"], timeframe=["today 12-m"])
        assert session.kw_list == ["Python"]

    def test_multiple_geos_creates_comparison_items(self) -> None:
        session = _make_session()
        with patch.object(session, "_tokens"):
            session.build_payload(["Python"], geo="US")


class TestTopCharts:
    def test_invalid_date_raises_value_error(self) -> None:
        session = _make_session()
        with pytest.raises(ValueError, match="year"):
            session.top_charts("not-a-year")

    def test_none_date_raises_value_error(self) -> None:
        session = _make_session()
        with pytest.raises(ValueError):
            session.top_charts(None)  # type: ignore[arg-type]

    def test_valid_int_year(self) -> None:
        session = _make_session()
        mock_response = {
            "topCharts": [{"listItems": [{"title": "item1"}]}]
        }
        with patch.object(session, "_get_data", return_value=mock_response):
            result = session.top_charts(2023)
        assert result == [{"title": "item1"}]

    def test_valid_string_year(self) -> None:
        session = _make_session()
        mock_response = {
            "topCharts": [{"listItems": [{"title": "item1"}]}]
        }
        with patch.object(session, "_get_data", return_value=mock_response):
            result = session.top_charts("2023")
        assert result == [{"title": "item1"}]

    def test_empty_top_charts_returns_none(self) -> None:
        session = _make_session()
        mock_response = {"topCharts": []}
        with patch.object(session, "_get_data", return_value=mock_response):
            result = session.top_charts(2023)
        assert result is None


class TestTrendingSearches:
    def test_returns_list_for_pn(self) -> None:
        session = _make_session()
        mock_response = {"united_states": ["AI", "Python"]}
        with patch.object(session, "_get_data", return_value=mock_response):
            result = session.trending_searches(pn="united_states")
        assert result == ["AI", "Python"]

    def test_returns_list_type(self) -> None:
        session = _make_session()
        mock_response = {"germany": ["Bayern", "Bundesliga"]}
        with patch.object(session, "_get_data", return_value=mock_response):
            result = session.trending_searches(pn="germany")
        assert isinstance(result, list)


class TestRelatedQueriesWidgets:
    def test_empty_widget_list_returns_empty_dict(self) -> None:
        session = _make_session()
        session.related_queries_widget_list = []
        result = session.related_queries()
        assert result == {}

    def test_empty_topics_widget_list_returns_empty_dict(self) -> None:
        session = _make_session()
        session.related_topics_widget_list = []
        result = session.related_topics()
        assert result == {}
