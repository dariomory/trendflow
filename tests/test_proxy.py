"""Tests for trendflow._proxy (ProxyPool) and the fetcher's per-query rotation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trendflow._fetcher import GoogleTrendsFetcher, _should_rotate
from trendflow._proxy import ProxyPool
from trendflow._trends_http.batchexecute import UnknownRpcError
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError
from trendflow.enums import Region


class TestProxyPool:
    def test_rotates_round_robin_and_wraps(self) -> None:
        pool = ProxyPool(["http://a:1", "http://b:2"])
        assert pool.current() == "http://a:1"
        pool.advance()
        assert pool.current() == "http://b:2"
        pool.advance()
        assert pool.current() == "http://a:1"

    def test_size_ignores_blank_entries(self) -> None:
        assert ProxyPool(["http://a:1", "   ", "http://b:2"]).size == 2

    def test_empty_pool_rejected(self) -> None:
        with pytest.raises(ValueError, match="no usable proxy URLs"):
            ProxyPool([])

    def test_blank_only_pool_rejected(self) -> None:
        with pytest.raises(ValueError, match="no usable proxy URLs"):
            ProxyPool(["  "])

    def test_malformed_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid proxy URL"):
            ProxyPool(["not a url"])


def _response_error(status: int) -> ResponseError:
    response = MagicMock()
    response.status_code = status
    return ResponseError("boom", response)


class TestShouldRotate:
    def test_rotates_on_429(self) -> None:
        assert _should_rotate(TooManyRequestsError("boom", MagicMock())) is True

    def test_rotates_on_403(self) -> None:
        assert _should_rotate(_response_error(403)) is True

    def test_does_not_rotate_on_404(self) -> None:
        assert _should_rotate(_response_error(404)) is False

    def test_does_not_rotate_on_renamed_rpc(self) -> None:
        # A renamed rpc id fails identically on every exit IP.
        assert _should_rotate(UnknownRpcError("fXqlme")) is False

    def test_rotates_on_network_error(self) -> None:
        assert _should_rotate(OSError("connection reset")) is True


def _fetcher_with_pool(proxies: list[str], **kwargs: object) -> tuple[GoogleTrendsFetcher, MagicMock]:
    """Build a fetcher whose session is a mock, so rotation can be driven directly."""
    with patch("trendflow._fetcher.GoogleTrendsHttpSession") as session_cls:
        session = MagicMock()
        session_cls.return_value = session
        fetcher = GoogleTrendsFetcher(proxies=proxies, **kwargs)  # type: ignore[arg-type]
    return fetcher, session


class TestFetcherRotation:
    def test_current_proxy_exposed(self) -> None:
        fetcher, _ = _fetcher_with_pool(["http://a:1", "http://b:2"])
        assert fetcher.current_proxy == "http://a:1"

    def test_no_pool_means_no_current_proxy(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession"):
            assert GoogleTrendsFetcher().current_proxy is None

    def test_advances_after_429_then_succeeds(self) -> None:
        rotations: list[int] = []
        fetcher, session = _fetcher_with_pool(
            ["http://bad:1", "http://good:2"],
            on_proxy_rotate=lambda attempt, _error: rotations.append(attempt),
        )
        session.trending_searches.side_effect = [
            TooManyRequestsError("boom", MagicMock()),
            [["AI", 100, 5]],
        ]

        result = fetcher.trending_now(Region.US)

        assert len(result.results) == 1
        assert rotations == [1]
        assert fetcher.current_proxy == "http://good:2"
        session.set_proxy.assert_called_once_with("http://good:2")

    def test_gives_up_after_every_proxy(self) -> None:
        fetcher, session = _fetcher_with_pool(["http://a:1", "http://b:2"])
        session.trending_searches.side_effect = TooManyRequestsError("boom", MagicMock())

        with pytest.raises(TooManyRequestsError):
            fetcher.trending_now(Region.US)

        assert session.trending_searches.call_count == 2

    def test_does_not_rotate_on_404(self) -> None:
        fetcher, session = _fetcher_with_pool(["http://a:1", "http://b:2"])
        session.trending_searches.side_effect = _response_error(404)

        with pytest.raises(ResponseError):
            fetcher.trending_now(Region.US)

        assert session.trending_searches.call_count == 1

    def test_max_proxy_attempts_caps_rotation(self) -> None:
        fetcher, session = _fetcher_with_pool(
            ["http://a:1", "http://b:2", "http://c:3", "http://d:4"],
            max_proxy_attempts=2,
        )
        session.trending_searches.side_effect = TooManyRequestsError("boom", MagicMock())

        with pytest.raises(TooManyRequestsError):
            fetcher.trending_now(Region.US)

        assert session.trending_searches.call_count == 2

    def test_session_receives_first_proxy(self) -> None:
        with patch("trendflow._fetcher.GoogleTrendsHttpSession") as session_cls:
            GoogleTrendsFetcher(proxies=["http://a:1", "http://b:2"])
        assert session_cls.call_args.kwargs["proxies"] == ["http://a:1"]
