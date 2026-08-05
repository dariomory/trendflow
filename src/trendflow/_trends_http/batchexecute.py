"""
Client for Google Trends' ``batchexecute`` RPC endpoint.

This is the transport behind the current trends.google.com UI. It replaces the retired
``hottrends`` / ``dailytrends`` / ``realtimetrends`` endpoints, which now return HTTP 404.
"""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from typing import Any

import httpx

from trendflow._trends_http.endpoints import BATCH_EXECUTE, HTTP_TOO_MANY_REQUESTS
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError

# ``fXqlme``: rising/top searches. With an empty keyword it returns trending searches.
RPC_TRENDING = "fXqlme"
# ``DqDTgb``: the full geo hierarchy -- every country with its subregions.
RPC_GEO_LIST = "DqDTgb"


class UnknownRpcError(Exception):
    """
    Google returned no frame for the RPC that was called.

    That is the signature of an identifier renamed on Google's side.
    """

    def __init__(self, rpc_id: str) -> None:
        super().__init__(
            f"Google returned no data for RPC {rpc_id!r}. This usually means the RPC "
            f"identifier changed on Google's side. Override it with the `rpc_ids` argument, "
            f"and please open an issue at https://github.com/dariomory/trendflow/issues",
        )
        self.rpc_id = rpc_id


def parse_batch_execute(text: str, rpc_id: str) -> Any:
    """
    Unwrap the chunked envelope Google wraps RPC responses in.

    The body is ``)]}'`` followed by repeating ``<length>\\n<json>`` frames; the payload sits
    inside a ``["wrb.fr", <rpc_id>, "<json string>"]`` frame.
    """
    result: Any = None
    body = text.removeprefix(")]}'\n")
    for line in body.split("\n"):
        trimmed = line.strip()
        if not trimmed.startswith("["):
            continue
        try:
            frames = json.loads(trimmed)
        except json.JSONDecodeError:
            continue
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if not isinstance(frame, list) or len(frame) < 3:
                continue
            if frame[0] != "wrb.fr" or frame[1] != rpc_id or not isinstance(frame[2], str):
                continue
            try:
                result = json.loads(frame[2])
            except json.JSONDecodeError:
                continue
    return result


class BatchExecuteClient:
    """Minimal client for the anonymous ``batchexecute`` RPCs."""

    def __init__(
        self,
        hl: str,
        timeout: httpx.Timeout | tuple[float, float] | float,
        headers: dict[str, str],
        rpc_ids: Mapping[str, str] | None = None,
        proxy: str | None = None,
    ) -> None:
        self.hl = hl
        self.timeout = timeout
        self.headers = headers
        self.proxy = proxy
        ids = dict(rpc_ids or {})
        self.trending_rpc_id = ids.get("trending", RPC_TRENDING)
        self.geo_list_rpc_id = ids.get("geo_list", RPC_GEO_LIST)

    def call(self, rpc_id: str, payload: Any) -> Any:
        """
        Invoke one RPC and return its decoded payload.

        Raises :class:`UnknownRpcError` when the response carries no frame for ``rpc_id``,
        which distinguishes a renamed identifier from a genuinely empty result.
        """
        params = {
            "rpcids": rpc_id,
            "source-path": "/explore",
            "hl": self.hl,
            "soc-app": "1",
            "soc-platform": "1",
            "soc-device": "1",
            "_reqid": str(random.randint(100000, 999999)),  # noqa: S311 - cache-buster, not crypto
            "rt": "c",
        }
        data = {"f.req": json.dumps([[[rpc_id, json.dumps(payload), None, "generic"]]])}
        headers = {
            **self.headers,
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
        }

        client_kwargs: dict[str, Any] = {"timeout": self.timeout, "headers": headers}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        with httpx.Client(**client_kwargs) as client:
            response = client.post(BATCH_EXECUTE, params=params, data=data)

        if response.status_code == HTTP_TOO_MANY_REQUESTS:
            raise TooManyRequestsError.from_response(response)
        if response.status_code != 200:
            raise ResponseError.from_response(response)
        parsed = parse_batch_execute(response.text, rpc_id)
        if parsed is None:
            raise UnknownRpcError(rpc_id)
        return parsed

    def trending_searches(self, geo: str, window: int) -> list[list[Any]]:
        """
        Trending searches for ``geo`` (``"Worldwide"`` or a country code such as ``"US"``).

        Returns raw ``[term, growth_percent, volume_index]`` rows.
        """
        data = self.call(self.trending_rpc_id, [[[geo, "", window, None, 2]], 1, self.hl, None, None, 0])
        try:
            rows = data[0][0][1]
        except (TypeError, IndexError, KeyError):
            return []
        return list(rows) if isinstance(rows, list) else []

    def geo_list(self) -> Any:
        """The full geo hierarchy: ``[code, name, slug]`` per country, each with subregions."""
        return self.call(self.geo_list_rpc_id, [self.hl, 1, 1])
