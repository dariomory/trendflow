"""Tests for trendflow._trends_http.exceptions."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError


def _make_response(status_code: int) -> httpx.Response:
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    return mock


class TestResponseError:
    def test_message_in_args(self) -> None:
        response = _make_response(500)
        err = ResponseError("something went wrong", response)
        assert "something went wrong" in str(err)

    def test_response_attached(self) -> None:
        response = _make_response(500)
        err = ResponseError("fail", response)
        assert err.response is response

    def test_is_exception(self) -> None:
        response = _make_response(500)
        err = ResponseError("fail", response)
        assert isinstance(err, Exception)

    def test_from_response_classmethod(self) -> None:
        response = _make_response(503)
        err = ResponseError.from_response(response)
        assert isinstance(err, ResponseError)
        assert "503" in str(err)
        assert err.response is response

    def test_from_response_message_format(self) -> None:
        response = _make_response(404)
        err = ResponseError.from_response(response)
        assert "404" in str(err)
        assert "Google" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        response = _make_response(500)
        with pytest.raises(ResponseError) as exc_info:
            raise ResponseError("test error", response)
        assert exc_info.value.response is response


class TestTooManyRequestsError:
    def test_is_response_error_subclass(self) -> None:
        response = _make_response(429)
        err = TooManyRequestsError("rate limited", response)
        assert isinstance(err, ResponseError)

    def test_is_exception(self) -> None:
        response = _make_response(429)
        err = TooManyRequestsError("rate limited", response)
        assert isinstance(err, Exception)

    def test_from_response_returns_too_many_requests_error(self) -> None:
        response = _make_response(429)
        err = TooManyRequestsError.from_response(response)
        assert isinstance(err, TooManyRequestsError)

    def test_response_attached(self) -> None:
        response = _make_response(429)
        err = TooManyRequestsError("rate limited", response)
        assert err.response is response

    def test_can_catch_as_response_error(self) -> None:
        response = _make_response(429)
        with pytest.raises(ResponseError):
            raise TooManyRequestsError("rate limited", response)
