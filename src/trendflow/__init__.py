from trendflow._fetcher import (
    TRENDING_WINDOW_RISING,
    TRENDING_WINDOW_TOP,
    GoogleTrendsFetcher,
    TrendsFetcher,
)
from trendflow._providers import TrendingBackend
from trendflow._trends_http.batchexecute import UnknownRpcError
from trendflow.enums import ExportFormat, Region, Resolution, SearchProperty, Timeframe
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RelatedQuery,
    RelatedResult,
    TopicSuggestion,
    TrendingArticle,
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
    "SearchProperty",
    "Timeframe",
    "TopicSuggestion",
    "TrendingArticle",
    "TrendingBackend",
    "TrendingItem",
    "TrendingResult",
    "TrendPoint",
    "TrendsFetcher",
    "UnknownRpcError",
]
