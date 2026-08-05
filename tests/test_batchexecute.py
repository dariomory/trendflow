"""Tests for trendflow._trends_http.batchexecute (the RPC endpoint behind Trending Now)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from trendflow._trends_http.batchexecute import (
    RPC_GEO_LIST,
    RPC_TRENDING,
    BatchExecuteClient,
    UnknownRpcError,
    parse_batch_execute,
)
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError

TRENDING_PAYLOAD: Any = [[["", [["fifa world cup 2026", 3950, 7], ["iphone 17", 850, 6]]]]]


def envelope(rpc_id: str, payload: Any) -> str:
    """The real response shape: ``)]}'`` then repeating ``<length>\\n<json>`` frames."""
    frame = json.dumps([["wrb.fr", rpc_id, json.dumps(payload), None, None, None, "generic"]])
    return f")]}}'\n\n{len(frame)}\n{frame}\n"


class TestParseBatchExecute:
    def test_unwraps_payload_for_requested_rpc(self) -> None:
        assert parse_batch_execute(envelope(RPC_TRENDING, TRENDING_PAYLOAD), RPC_TRENDING) == TRENDING_PAYLOAD

    def test_ignores_other_rpc_frames(self) -> None:
        assert parse_batch_execute(envelope("other", TRENDING_PAYLOAD), RPC_TRENDING) is None

    def test_malformed_inner_payload(self) -> None:
        frame = json.dumps([["wrb.fr", RPC_TRENDING, "{not json", None, None, "generic"]])
        assert parse_batch_execute(f")]}}'\n\n{len(frame)}\n{frame}\n", RPC_TRENDING) is None

    def test_empty_body(self) -> None:
        assert parse_batch_execute("", RPC_TRENDING) is None


def _client(status: int = 200, text: str = "", rpc_ids: dict[str, str] | None = None) -> tuple[BatchExecuteClient, Any]:
    client = BatchExecuteClient(hl="en", timeout=5, headers={}, rpc_ids=rpc_ids)
    response = MagicMock()
    response.status_code = status
    response.text = text
    http = MagicMock()
    http.__enter__.return_value.post.return_value = response
    return client, http


class TestBatchExecuteClient:
    def test_trending_searches_parses_rows(self) -> None:
        client, http = _client(text=envelope(RPC_TRENDING, TRENDING_PAYLOAD))
        with patch("httpx.Client", return_value=http):
            rows = client.trending_searches("US", 8)
        assert rows == [["fifa world cup 2026", 3950, 7], ["iphone 17", 850, 6]]

    def test_trending_searches_sends_geo_and_window(self) -> None:
        client, http = _client(text=envelope(RPC_TRENDING, TRENDING_PAYLOAD))
        with patch("httpx.Client", return_value=http):
            client.trending_searches("NL", 10)
        kwargs = http.__enter__.return_value.post.call_args.kwargs
        assert kwargs["params"]["rpcids"] == RPC_TRENDING
        assert json.loads(kwargs["data"]["f.req"])[0][0][1] == json.dumps(
            [[["NL", "", 10, None, 2]], 1, "en", None, None, 0],
        )

    def test_empty_rows_when_payload_has_none(self) -> None:
        client, http = _client(text=envelope(RPC_TRENDING, [[["", []]]]))
        with patch("httpx.Client", return_value=http):
            assert client.trending_searches("US", 8) == []

    def test_too_many_requests(self) -> None:
        client, http = _client(status=429)
        with patch("httpx.Client", return_value=http), pytest.raises(TooManyRequestsError):
            client.trending_searches("US", 8)

    def test_other_failure_raises_response_error(self) -> None:
        client, http = _client(status=500)
        with patch("httpx.Client", return_value=http), pytest.raises(ResponseError):
            client.trending_searches("US", 8)

    def test_renamed_rpc_reported(self) -> None:
        client, http = _client(text=envelope("someOtherId", TRENDING_PAYLOAD))
        with patch("httpx.Client", return_value=http), pytest.raises(UnknownRpcError) as exc:
            client.trending_searches("US", 8)
        assert exc.value.rpc_id == RPC_TRENDING
        assert "rpc_ids" in str(exc.value)

    def test_rpc_id_override_used(self) -> None:
        client, http = _client(text=envelope("newId", TRENDING_PAYLOAD), rpc_ids={"trending": "newId"})
        with patch("httpx.Client", return_value=http):
            rows = client.trending_searches("US", 8)
        assert len(rows) == 2
        assert http.__enter__.return_value.post.call_args.kwargs["params"]["rpcids"] == "newId"

    def test_geo_list_uses_its_own_rpc(self) -> None:
        client, http = _client(text=envelope(RPC_GEO_LIST, [[[["US", "United States", "united states"]]]]))
        with patch("httpx.Client", return_value=http):
            client.geo_list()
        assert http.__enter__.return_value.post.call_args.kwargs["params"]["rpcids"] == RPC_GEO_LIST
