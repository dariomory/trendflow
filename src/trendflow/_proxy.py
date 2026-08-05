"""
Round-robin pool of proxy URLs.

Rotation is deliberately **per operation, not per request**. Google binds the ``NID`` cookie
and the widget token it hands out to the IP that requested them, so sending the follow-up
widgetdata call from a different exit IP earns an immediate HTTP 429. A pool therefore pins
one proxy for the whole of a query and only advances when that query fails.

The same reasoning applies to rotating-gateway providers: point the pool at a sticky session
endpoint, not a per-request rotating one.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse


class ProxyPool:
    """Holds proxy URLs and tracks which one is currently pinned."""

    def __init__(self, urls: Sequence[str]) -> None:
        cleaned = [url.strip() for url in urls if url and url.strip()]
        for url in cleaned:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                msg = f"Invalid proxy URL: {url}"
                raise ValueError(msg)
        if not cleaned:
            msg = "`proxies` was given no usable proxy URLs"
            raise ValueError(msg)
        self._urls = cleaned
        self._index = 0

    @property
    def size(self) -> int:
        return len(self._urls)

    @property
    def index(self) -> int:
        return self._index

    def current(self) -> str:
        """The proxy currently pinned for requests."""
        return self._urls[self._index]

    def advance(self) -> None:
        """Move to the next proxy, wrapping around at the end of the list."""
        self._index = (self._index + 1) % len(self._urls)
