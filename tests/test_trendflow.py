"""Tests for `trendflow` package — public API surface."""

import trendflow
from trendflow import (
    Client,
    ExportFormat,
    GoogleTrendsFetcher,
    InterestByRegionResult,
    InterestOverTimeResult,
    Region,
    RelatedQuery,
    RelatedResult,
    Resolution,
    Timeframe,
    TrendingItem,
    TrendingResult,
    TrendPoint,
    TrendsFetcher,
)
from trendflow.models import RegionalInterestRow


def test_import():
    """Verify the package can be imported."""
    assert trendflow


def test_client_is_alias_for_google_trends_fetcher():
    assert Client is GoogleTrendsFetcher


def test_all_enums_exported():
    assert Region is not None
    assert Timeframe is not None
    assert Resolution is not None
    assert ExportFormat is not None


def test_all_models_exported():
    assert TrendPoint is not None
    assert InterestOverTimeResult is not None
    assert RegionalInterestRow is not None
    assert InterestByRegionResult is not None
    assert TrendingItem is not None
    assert TrendingResult is not None
    assert RelatedQuery is not None
    assert RelatedResult is not None


def test_trends_fetcher_protocol_exported():
    assert TrendsFetcher is not None


def test_google_trends_fetcher_exported():
    assert GoogleTrendsFetcher is not None
