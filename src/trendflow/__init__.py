from trendflow._fetcher import GoogleTrendsFetcher, TrendsFetcher
from trendflow.enums import ExportFormat, Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedQuery,
    RelatedResult,
    TrendingItem,
    TrendingResult,
    TrendPoint,
)

Client = GoogleTrendsFetcher

__all__ = [
    "Client",
    "ExportFormat",
    "GoogleTrendsFetcher",
    "InterestByRegionResult",
    "InterestOverTimeResult",
    "RelatedQuery",
    "RelatedResult",
    "Region",
    "Resolution",
    "Timeframe",
    "TrendingItem",
    "TrendingResult",
    "TrendPoint",
    "TrendsFetcher",
]
