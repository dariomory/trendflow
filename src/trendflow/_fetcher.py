from __future__ import annotations

from typing import Protocol, runtime_checkable

from trendflow import _parsers
from trendflow._trends_http import GoogleTrendsHttpSession
from trendflow.enums import Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedResult,
    TrendingResult,
)

# `trending_searches(pn=...)` response keys (see `GoogleTrendsHttpSession.trending_searches`).
TRENDING_PN: dict[Region, str] = {
    Region.US: "united_states",
    Region.GB: "united_kingdom",
    Region.DE: "germany",
    Region.FR: "france",
    Region.IT: "italy",
    Region.ES: "spain",
    Region.CA: "canada",
    Region.AU: "australia",
    Region.JP: "japan",
    Region.IN: "india",
    Region.BR: "brazil",
    Region.MX: "mexico",
    Region.NL: "netherlands",
    Region.SE: "sweden",
    Region.PL: "poland",
    Region.TR: "turkey",
}


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

    def trending_now(self, region: Region) -> TrendingResult: ...

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

    def trending_now(self, region: Region) -> TrendingResult:
        if region is Region.WORLDWIDE:
            msg = "Trending searches require a specific country; use e.g. Region.US"
            raise ValueError(msg)
        pn = TRENDING_PN.get(region)
        if pn is None:
            msg = f"No trending_searches mapping for region {region!r}"
            raise ValueError(msg)
        titles = self._req.trending_searches(pn=pn)
        return _parsers.trending_result_from_titles(titles)

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
