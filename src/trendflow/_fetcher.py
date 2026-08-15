from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Final, Protocol, TypeVar, runtime_checkable

from trendflow import _parsers
from trendflow._providers import (
    RpcTrendingProvider,
    RssTrendingProvider,
    TrendingBackend,
    TrendingProvider,
)
from trendflow._proxy import ProxyPool
from trendflow._trends_http import GoogleTrendsHttpSession
from trendflow._trends_http.batchexecute import UnknownRpcError
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError
from trendflow.enums import Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedResult,
    TopicSuggestion,
    TrendingResult,
)

TRENDING_WINDOW_RISING: Final[int] = 8
TRENDING_WINDOW_TOP: Final[int] = 10


def _trending_geo(region: Region | str) -> str:
    """Google's RPC takes the literal ``"Worldwide"`` rather than an empty geo."""
    value = region.value if isinstance(region, Region) else str(region)
    return "Worldwide" if value == "" else value


T = TypeVar("T")

HTTP_FORBIDDEN: Final[int] = 403


def _should_rotate(error: Exception) -> bool:
    """
    Whether a failure is worth retrying on a different exit IP.

    A 429 or a network error says "this IP is blocked". A 404 says the endpoint is gone, and a
    renamed RPC id fails identically everywhere, so rotating would only burn the pool.
    """
    if isinstance(error, TooManyRequestsError):
        return True
    if isinstance(error, ResponseError):
        return error.response.status_code == HTTP_FORBIDDEN
    if isinstance(error, UnknownRpcError):
        return False
    return True


def _hl_from_language(language: str) -> str:
    if "-" in language:
        return language
    return f"{language}-US"


@runtime_checkable
class TrendsFetcher(Protocol):
    """Strategy for retrieving Trends data (swap in tests or alternate backends)."""

    def interest_over_time(
        self,
        keywords: list[str],
        timeframe: Timeframe,
        region: Region,
    ) -> InterestOverTimeResult: ...

    def interest_by_region(
        self,
        keyword: str,
        resolution: Resolution,
        region: Region = Region.US,
    ) -> InterestByRegionResult: ...

    def trending_now(
        self,
        region: Region | str = Region.WORLDWIDE,
        window: int = ...,
        backend: TrendingBackend = ...,
    ) -> TrendingResult: ...

    def related_queries(self, keyword: str) -> RelatedResult: ...

    def suggestions(self, query: str) -> list[TopicSuggestion]: ...


class GoogleTrendsFetcher:
    """Fetches data via the in-tree :class:`GoogleTrendsHttpSession`."""

    def __init__(
        self,
        language: str = "en",
        timeout: int = 10,
        proxies: Sequence[str] | None = None,
        max_proxy_attempts: int | None = None,
        on_proxy_rotate: Callable[[int, Exception], None] | None = None,
    ) -> None:
        """
        ``proxies`` is a list of proxy URLs to rotate through, from any mix of providers.

        One proxy is pinned per query and the pool advances only when a query fails, because
        Google binds its cookie and widget token to the exit IP. ``max_proxy_attempts``
        defaults to the pool size, capped at 5; ``on_proxy_rotate(attempt, error)`` is called
        each time the pool advances.
        """
        to = (timeout, max(timeout * 2, timeout + 5))
        self._pool = ProxyPool(proxies) if proxies else None
        default_attempts = min(self._pool.size, 5) if self._pool else 1
        self._max_proxy_attempts = max_proxy_attempts if max_proxy_attempts is not None else default_attempts
        self._on_proxy_rotate = on_proxy_rotate
        self._req = GoogleTrendsHttpSession(
            hl=_hl_from_language(language),
            tz=360,
            timeout=to,
            proxies=[self._pool.current()] if self._pool else "",
        )
        self._rpc_trending: TrendingProvider = RpcTrendingProvider(self._req.rpc_client)
        self._rss_trending: TrendingProvider = RssTrendingProvider(self._req.rss_client)

    @property
    def current_proxy(self) -> str | None:
        """The proxy currently pinned for queries, if a pool is configured."""
        return self._pool.current() if self._pool else None

    def _with_rotation(self, operation: Callable[[], T]) -> T:
        """
        Run a query, moving to the next proxy and re-seeding the cookie jar if it fails in a
        way a different exit IP could fix.
        """
        if self._pool is None:
            return operation()

        attempts = max(1, min(self._pool.size, self._max_proxy_attempts))
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except Exception as error:
                if not _should_rotate(error) or attempt == attempts:
                    raise
                self._pool.advance()
                # The cookie and any cached widget token belong to the previous exit IP.
                self._req.set_proxy(self._pool.current())
                if self._on_proxy_rotate is not None:
                    self._on_proxy_rotate(attempt, error)
        raise AssertionError("unreachable")  # pragma: no cover

    def interest_over_time(
        self,
        keywords: list[str],
        timeframe: Timeframe,
        region: Region,
    ) -> InterestOverTimeResult:
        def run() -> InterestOverTimeResult:
            self._req.build_payload(
                keywords,
                cat=0,
                timeframe=timeframe.value,
                geo=region.value,
                gprop="",
            )
            default = self._req.interest_over_time()
            return _parsers.interest_over_time_to_result(default, keywords, self._req.geo)

        return self._with_rotation(run)

    def interest_by_region(
        self,
        keyword: str,
        resolution: Resolution,
        region: Region = Region.US,
    ) -> InterestByRegionResult:
        def run() -> InterestByRegionResult:
            self._req.build_payload(
                [keyword],
                cat=0,
                timeframe=Timeframe.PAST_YEAR.value,
                geo=region.value,
                gprop="",
            )
            default = self._req.interest_by_region(
                resolution=resolution.value,
                inc_low_vol=True,
                inc_geo_code=False,
            )
            if not default.get("geoMapData"):
                return InterestByRegionResult(keyword=keyword, resolution=resolution, rows=[])
            return _parsers.interest_by_region_to_result(default, keyword, [keyword], resolution)

        return self._with_rotation(run)

    def trending_now(
        self,
        region: Region | str = Region.WORLDWIDE,
        window: int = TRENDING_WINDOW_RISING,
        backend: TrendingBackend = "auto",
    ) -> TrendingResult:
        """
        Trending searches for ``region``.

        Accepts any country code, not a fixed list, and worldwide works too. ``window``
        selects fastest-growing (:data:`TRENDING_WINDOW_RISING`) versus highest-volume
        (:data:`TRENDING_WINDOW_TOP`) results.

        ``backend`` selects the source:

        * ``"rpc"`` -- 50 items with growth percentages and volume.
        * ``"rss"`` -- 10 items with the **news articles** behind each trend, which the RPC
          does not carry, but no growth figures. ``window`` does not apply: Google ignores
          it on the feed. There is no worldwide feed, so a country code is required.
        * ``"auto"`` (default) -- the RPC, falling back to RSS if it fails. RPC first
          because it returns five times the items with real growth numbers; defaulting to
          RSS would quietly degrade results.

        :attr:`TrendingResult.source` reports which one answered.
        """
        geo = _trending_geo(region)

        def run(provider: TrendingProvider) -> TrendingResult:
            return TrendingResult(results=provider.fetch(geo, window), source=provider.source)

        if backend == "rpc":
            return self._with_rotation(lambda: run(self._rpc_trending))
        if backend == "rss":
            return self._with_rotation(lambda: run(self._rss_trending))

        def auto() -> TrendingResult:
            try:
                return run(self._rpc_trending)
            except Exception:  # noqa: BLE001 - the feed is a separate source; any RPC failure falls back
                return run(self._rss_trending)

        return self._with_rotation(auto)

    def related_queries(self, keyword: str) -> RelatedResult:
        def run() -> RelatedResult:
            self._req.build_payload(
                [keyword],
                cat=0,
                timeframe=Timeframe.PAST_YEAR.value,
                geo="",
                gprop="",
            )
            raw = self._req.related_queries()
            return _parsers.related_queries_to_result(raw, keyword)

        return self._with_rotation(run)

    def suggestions(self, query: str) -> list[TopicSuggestion]:
        """
        Entity suggestions for a partial query -- the picker behind the UI's "Topic" results.

        Pass a returned ``mid`` as a keyword to any query method to measure the **topic**
        rather than the literal phrase; a topic aggregates every spelling and translation of
        the same concept, so it usually scores far higher than the raw string.

        Needs no cookie and no proxy: this RPC answers on IPs the widgetdata endpoints
        reject.
        """
        return self._with_rotation(
            lambda: _parsers.suggestion_rows_to_topics(self._req.suggestions(query)),
        )

    def geo_list(self) -> Any:
        """Every region Google accepts: ``[code, name, slug]`` per country, with subregions."""
        return self._with_rotation(self._req.geo_list)
