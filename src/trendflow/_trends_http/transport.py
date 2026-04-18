from __future__ import annotations

import json
import logging
from collections.abc import Mapping, MutableMapping
from typing import Any, Literal

import httpx

from trendflow._trends_http.endpoints import BASE_TRENDS_URL, HTTP_TOO_MANY_REQUESTS
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError

logger = logging.getLogger(__name__)

Method = Literal["get", "post"]


def _normalize_timeout(timeout: httpx.Timeout | tuple[float, float] | float) -> httpx.Timeout:
    """Coerce session timeout values to :class:`httpx.Timeout` (ty / httpx 0.28 compatible)."""
    if isinstance(timeout, httpx.Timeout):
        return timeout
    if isinstance(timeout, tuple):
        a, b = float(timeout[0]), float(timeout[1])
        return httpx.Timeout(b, connect=a, read=b)
    return httpx.Timeout(float(timeout))


def _extra_for_httpx(extra: Mapping[str, Any]) -> dict[str, Any]:
    """Map legacy ``proxies`` dict to httpx 0.28 ``proxy`` (single URL)."""
    out = {k: v for k, v in extra.items() if k != "proxies"}
    if "proxies" in extra:
        px = extra["proxies"]
        if isinstance(px, dict) and px:
            out["proxy"] = next(iter(px.values()))
        elif px is not None:
            out["proxy"] = px
    return out


def _json_content_type(content_type: str) -> bool:
    ct = content_type.lower()
    return "application/json" in ct or "application/javascript" in ct or "text/javascript" in ct


class TrendsJsonTransport:
    """Low-level Trends host requests: NID cookie + JSON responses."""

    def __init__(
        self,
        *,
        hl: str,
        tz: int,
        timeout: httpx.Timeout | tuple[float, float] | float,
        headers: MutableMapping[str, str],
        extra_client_args: Mapping[str, Any],
        proxy_urls: list[str],
        retries: int,
    ) -> None:
        self._hl = hl
        self._tz = tz
        self.timeout = _normalize_timeout(timeout)
        self.headers = headers
        self._extra_client_args = dict(extra_client_args)
        self._proxy_urls = proxy_urls
        self._retries = retries
        self._proxy_index = 0
        self.cookies: dict[str, str] = self._fetch_nid_cookies()

    @property
    def proxy_index(self) -> int:
        return self._proxy_index

    def _explore_cookie_url(self) -> str:
        return f"{BASE_TRENDS_URL}/explore/?geo={self._hl[-2:]}"

    def _fetch_nid_cookies(self) -> dict[str, str]:
        url = self._explore_cookie_url()
        while True:
            if "proxies" in self._extra_client_args:
                try:
                    r = httpx.get(url, timeout=self.timeout, **_extra_for_httpx(self._extra_client_args))
                    return {k: v for k, v in r.cookies.items() if k == "NID"}
                except Exception:
                    continue
            proxy_url: str | None = None
            if self._proxy_urls:
                proxy_url = self._proxy_urls[self._proxy_index]
            try:
                get_kw = _extra_for_httpx(self._extra_client_args)
                if proxy_url is not None:
                    get_kw["proxy"] = proxy_url
                r = httpx.get(
                    url,
                    timeout=self.timeout,
                    **get_kw,
                )
                return {k: v for k, v in r.cookies.items() if k == "NID"}
            except httpx.ProxyError:
                logger.warning("Proxy error; rotating proxy")
                if len(self._proxy_urls) > 1:
                    self._proxy_urls.remove(self._proxy_urls[self._proxy_index])
                else:
                    raise
                continue

    def advance_proxy(self) -> None:
        if not self._proxy_urls:
            return
        if self._proxy_index < len(self._proxy_urls) - 1:
            self._proxy_index += 1
        else:
            self._proxy_index = 0

    def request_json(
        self,
        url: str,
        method: Method,
        *,
        trim_chars: int = 0,
        **kwargs: Any,
    ) -> Any:
        proxy_url: str | None = None
        if self._proxy_urls:
            self.cookies = self._fetch_nid_cookies()
            proxy_url = self._proxy_urls[self._proxy_index]

        transport = httpx.HTTPTransport(retries=self._retries) if self._retries > 0 else None

        client_kwargs: dict[str, Any] = {
            "timeout": self.timeout,
            "headers": dict(self.headers),
        }
        if proxy_url is not None:
            client_kwargs["proxy"] = proxy_url
        if transport is not None:
            client_kwargs["transport"] = transport

        merged = {**self._extra_client_args, **kwargs}
        req_kwargs = _extra_for_httpx(merged)
        with httpx.Client(**client_kwargs) as client:
            if method == "post":
                response = client.post(url, cookies=self.cookies, **req_kwargs)
            else:
                response = client.get(url, cookies=self.cookies, **req_kwargs)

        ct = response.headers.get("content-type") or ""
        if response.status_code == 200 and _json_content_type(ct):
            self.advance_proxy()
            return json.loads(response.text[trim_chars:])
        if response.status_code == HTTP_TOO_MANY_REQUESTS:
            raise TooManyRequestsError.from_response(response)
        raise ResponseError.from_response(response)
