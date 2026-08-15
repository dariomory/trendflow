from trendflow._fetcher import (
    TRENDING_WINDOW_RISING,
    TRENDING_WINDOW_TOP,
    GoogleTrendsFetcher,
    TrendsFetcher,
)
from trendflow._trends_http.batchexecute import UnknownRpcError
from trendflow.enums import ExportFormat, Region, Resolution, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedQuery,
    RelatedResult,
    TopicSuggestion,
    TrendingItem,
    TrendingResult,
    TrendPoint,
)

Client = GoogleTrendsFetcher

__all__ = [
    "TRENDING_WINDOW_RISING",
    "TRENDING_WINDOW_TOP",
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
    "TopicSuggestion",
    "TrendingItem",
    "TrendingResult",
    "TrendPoint",
    "TrendsFetcher",
    "UnknownRpcError",
]
