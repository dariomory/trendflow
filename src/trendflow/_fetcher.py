from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from trendflow import _parsers
from trendflow._trends_http import GoogleTrendsHttpSession
from trendflow.enums import Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedResult,
    TrendingResult,
)

TRENDING_WINDOW_RISING: Final[int] = 8
TRENDING_WINDOW_TOP: Final[int] = 10


def _trending_geo(region: Region | str) -> str:
    """Google's RPC takes the literal ``"Worldwide"`` rather than an empty geo."""
    value = region.value if isinstance(region, Region) else str(region)
    return "Worldwide" if value == "" else value


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

    def trending_now(self, region: Region | str = Region.WORLDWIDE, window: int = ...) -> TrendingResult: ...

    def related_queries(self, keyword: str) -> RelatedResult: ...


class GoogleTrendsFetcher:
    """Fetches data via the in-tree :class:`GoogleTrendsHttpSession`."""

    def __init__(self, language: str = "en", timeout: int = 10) -> None:
        to = (timeout, max(timeout * 2, timeout + 5))
        self._req = GoogleTrendsHttpSession(hl=_hl_from_language(language), tz=360, timeout=to)

    def interest_over_time(
        self,
        keywords: list[str],
        timeframe: Timeframe,
        region: Region,
    ) -> InterestOverTimeResult:
        self._req.build_payload(
            keywords,
            cat=0,
            timeframe=timeframe.value,
            geo=region.value,
            gprop="",
        )
        default = self._req.interest_over_time()
        return _parsers.interest_over_time_to_result(default, keywords, self._req.geo)

    def interest_by_region(
        self,
        keyword: str,
        resolution: Resolution,
        region: Region = Region.US,
    ) -> InterestByRegionResult:
        self._req.build_payload(
            [keyword],
            cat=0,
            timeframe=Timeframe.PAST_YEAR.value,
            geo=region.value,
            gprop="",
        )
        default = self._req.interest_by_region(resolution=resolution.value, inc_low_vol=True, inc_geo_code=False)
        if not default.get("geoMapData"):
            return InterestByRegionResult(keyword=keyword, resolution=resolution, rows=[])
        return _parsers.interest_by_region_to_result(default, keyword, [keyword], resolution)

    def trending_now(
        self,
        region: Region | str = Region.WORLDWIDE,
        window: int = TRENDING_WINDOW_RISING,
    ) -> TrendingResult:
        """
        Trending searches for ``region``.

        Accepts any country code, not a fixed list, and worldwide works too. ``window``
        selects fastest-growing (:data:`TRENDING_WINDOW_RISING`) versus highest-volume
        (:data:`TRENDING_WINDOW_TOP`) results.
        """
        rows = self._req.trending_searches(geo=_trending_geo(region), window=window)
        return _parsers.trending_result_from_rows(rows)

    def related_queries(self, keyword: str) -> RelatedResult:
        self._req.build_payload(
            [keyword],
            cat=0,
            timeframe=Timeframe.PAST_YEAR.value,
            geo="",
            gprop="",
        )
        raw = self._req.related_queries()
        return _parsers.related_queries_to_result(raw, keyword)
