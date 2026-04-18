"""Tests for trendflow._trends_http.transport helper functions and TrendsJsonTransport."""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError
from trendflow._trends_http.transport import (
    TrendsJsonTransport,
    _extra_for_httpx,
    _json_content_type,
    _normalize_timeout,
)


class TestNormalizeTimeout:
    def test_httpx_timeout_passthrough(self) -> None:
        t = httpx.Timeout(10.0)
        assert _normalize_timeout(t) is t

    def test_float_becomes_httpx_timeout(self) -> None:
        result = _normalize_timeout(5.0)
        assert isinstance(result, httpx.Timeout)

    def test_int_becomes_httpx_timeout(self) -> None:
        result = _normalize_timeout(10)
        assert isinstance(result, httpx.Timeout)

    def test_tuple_sets_connect_and_read(self) -> None:
        result = _normalize_timeout((2.0, 10.0))
        assert isinstance(result, httpx.Timeout)
        assert result.connect == 2.0
        assert result.read == 10.0

    def test_tuple_values_coerced_to_float(self) -> None:
        result = _normalize_timeout((2, 10))
        assert result.connect == 2.0
        assert result.read == 10.0


class TestExtraForHttpx:
    def test_passes_through_non_proxies_keys(self) -> None:
        extra = {"verify": False, "follow_redirects": True}
        result = _extra_for_httpx(extra)
        assert result["verify"] is False
        assert result["follow_redirects"] is True

    def test_removes_proxies_key(self) -> None:
        extra = {"proxies": {"https://": "http://proxy:8080"}}
        result = _extra_for_httpx(extra)
        assert "proxies" not in result

    def test_maps_proxies_dict_to_proxy(self) -> None:
        extra = {"proxies": {"https://": "http://proxy:8080"}}
        result = _extra_for_httpx(extra)
        assert result["proxy"] == "http://proxy:8080"

    def test_maps_proxies_string_to_proxy(self) -> None:
        extra = {"proxies": "http://proxy:8080"}
        result = _extra_for_httpx(extra)
        assert result["proxy"] == "http://proxy:8080"

    def test_none_proxies_not_added(self) -> None:
        extra = {"proxies": None}
        result = _extra_for_httpx(extra)
        assert "proxy" not in result
        assert "proxies" not in result

    def test_empty_dict_stays_empty(self) -> None:
        result = _extra_for_httpx({})
        assert result == {}


class TestJsonContentType:
    def test_application_json(self) -> None:
        assert _json_content_type("application/json") is True

    def test_application_json_with_charset(self) -> None:
        assert _json_content_type("application/json; charset=utf-8") is True

    def test_application_javascript(self) -> None:
        assert _json_content_type("application/javascript") is True

    def test_text_javascript(self) -> None:
        assert _json_content_type("text/javascript") is True

    def test_text_html_is_false(self) -> None:
        assert _json_content_type("text/html") is False

    def test_text_plain_is_false(self) -> None:
        assert _json_content_type("text/plain") is False

    def test_empty_string_is_false(self) -> None:
        assert _json_content_type("") is False

    def test_case_insensitive(self) -> None:
        assert _json_content_type("Application/JSON") is True


def _make_transport(
    *,
    hl: str = "en-US",
    tz: int = 360,
    timeout: httpx.Timeout | tuple[float, float] | float = (2.0, 5.0),
    headers: MutableMapping[str, str] | None = None,
    extra_client_args: Mapping[str, Any] | None = None,
    proxy_urls: list[str] | None = None,
    retries: int = 0,
) -> TrendsJsonTransport:
    """Build a TrendsJsonTransport with _fetch_nid_cookies patched out."""
    with patch.object(TrendsJsonTransport, "_fetch_nid_cookies", return_value={"NID": "test"}):
        transport = TrendsJsonTransport(
            hl=hl,
            tz=tz,
            timeout=timeout,
            headers=headers if headers is not None else {},
            extra_client_args=extra_client_args if extra_client_args is not None else {},
            proxy_urls=proxy_urls if proxy_urls is not None else [],
            retries=retries,
        )
    return transport


class TestTrendsJsonTransportAdvanceProxy:
    def test_no_proxies_is_noop(self) -> None:
        transport = _make_transport(proxy_urls=[])
        transport.advance_proxy()
        assert transport.proxy_index == 0

    def test_single_proxy_wraps_to_zero(self) -> None:
        transport = _make_transport(proxy_urls=["http://proxy1:8080"])
        assert transport.proxy_index == 0
        transport.advance_proxy()
        assert transport.proxy_index == 0

    def test_two_proxies_advance(self) -> None:
        transport = _make_transport(proxy_urls=["http://p1:8080", "http://p2:8080"])
        assert transport.proxy_index == 0
        transport.advance_proxy()
        assert transport.proxy_index == 1

    def test_two_proxies_wraps_after_last(self) -> None:
        transport = _make_transport(proxy_urls=["http://p1:8080", "http://p2:8080"])
        transport.advance_proxy()  # → 1
        transport.advance_proxy()  # → 0 (wrap)
        assert transport.proxy_index == 0


class TestTrendsJsonTransportCookieUrl:
    def test_cookie_url_uses_last_two_chars_of_hl(self) -> None:
        transport = _make_transport(hl="en-US")
        url = transport._explore_cookie_url()
        assert url.endswith("?geo=US")

    def test_cookie_url_for_gb(self) -> None:
        transport = _make_transport(hl="en-GB")
        url = transport._explore_cookie_url()
        assert url.endswith("?geo=GB")


class TestTrendsJsonTransportRequestJson:
    def _mock_response(self, status_code: int, content_type: str, body: str) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.headers = {"content-type": content_type}
        resp.text = body
        return resp

    def test_get_returns_parsed_json(self) -> None:
        transport = _make_transport()
        payload = {"key": "value"}
        response = self._mock_response(200, "application/json", json.dumps(payload))

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            result = transport.request_json("https://example.com", "get")

        assert result == payload

    def test_post_calls_client_post(self) -> None:
        transport = _make_transport()
        payload = {"data": [1, 2, 3]}
        response = self._mock_response(200, "application/json", json.dumps(payload))

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response
            mock_client_cls.return_value = mock_client

            result = transport.request_json("https://example.com", "post")

        assert result == payload
        mock_client.post.assert_called_once()

    def test_trim_chars_strips_prefix(self) -> None:
        transport = _make_transport()
        response = self._mock_response(200, "application/json", ')]}\'\n{"x": 1}')

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            result = transport.request_json("https://example.com", "get", trim_chars=5)

        assert result == {"x": 1}

    def test_429_raises_too_many_requests(self) -> None:
        transport = _make_transport()
        response = self._mock_response(429, "application/json", "{}")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            with pytest.raises(TooManyRequestsError):
                transport.request_json("https://example.com", "get")

    def test_500_raises_response_error(self) -> None:
        transport = _make_transport()
        response = self._mock_response(500, "text/html", "<html>error</html>")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            with pytest.raises(ResponseError):
                transport.request_json("https://example.com", "get")

    def test_non_json_200_raises_response_error(self) -> None:
        transport = _make_transport()
        response = self._mock_response(200, "text/html", "<html></html>")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            with pytest.raises(ResponseError):
                transport.request_json("https://example.com", "get")

    def test_successful_request_advances_proxy(self) -> None:
        transport = _make_transport(proxy_urls=["http://p1:8080", "http://p2:8080"])
        response = self._mock_response(200, "application/json", "{}")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = response
            mock_client_cls.return_value = mock_client

            with patch.object(transport, "_fetch_nid_cookies", return_value={}):
                transport.request_json("https://example.com", "get")

        assert transport.proxy_index == 1
