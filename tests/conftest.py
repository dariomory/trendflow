"""Shared fixtures for the trendflow test suite."""

from __future__ import annotations

from datetime import datetime

import pytest

from trendflow.enums import Resolution
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RegionalInterestRow,
    RelatedQuery,
    RelatedResult,
    TrendingItem,
    TrendingResult,
    TrendPoint,
)


@pytest.fixture
def dt_jan1() -> datetime:
    return datetime(2024, 1, 1, 0, 0, 0)


@pytest.fixture
def dt_jan8() -> datetime:
    return datetime(2024, 1, 8, 0, 0, 0)


@pytest.fixture
def two_kw_points() -> list[TrendPoint]:
    return [
        TrendPoint(date=datetime(2024, 1, 1), scores={"Python": 80, "JavaScript": 70}),
        TrendPoint(date=datetime(2024, 1, 8), scores={"Python": 85, "JavaScript": 65}),
        TrendPoint(date=datetime(2024, 1, 15), scores={"Python": 90, "JavaScript": 60}),
    ]


@pytest.fixture
def iot_result(two_kw_points: list[TrendPoint]) -> InterestOverTimeResult:
    return InterestOverTimeResult(
        keywords=["Python", "JavaScript"],
        granularity="weekly",
        points=two_kw_points,
    )


@pytest.fixture
def empty_iot_result() -> InterestOverTimeResult:
    return InterestOverTimeResult(keywords=["Python"], granularity="unknown", points=[])


@pytest.fixture
def region_rows() -> list[RegionalInterestRow]:
    return [
        RegionalInterestRow(label="California", value=90),
        RegionalInterestRow(label="Texas", value=70),
    ]


@pytest.fixture
def ibr_result(region_rows: list[RegionalInterestRow]) -> InterestByRegionResult:
    return InterestByRegionResult(keyword="Python", resolution=Resolution.REGION, rows=region_rows)


@pytest.fixture
def trending_result() -> TrendingResult:
    return TrendingResult(
        results=[
            TrendingItem(title="AI tools", traffic="500K+", articles=[]),
            TrendingItem(title="Python 4", traffic="200K+", articles=[]),
        ]
    )


@pytest.fixture
def related_result() -> RelatedResult:
    return RelatedResult(
        top=[RelatedQuery(term="python tutorial", value=100)],
        rising=[RelatedQuery(term="python ai", breakout="+250%")],
    )


@pytest.fixture
def timeline_data_weekly() -> dict:
    """Two entries 7 days apart for granularity inference."""
    ts0 = int(datetime(2024, 1, 1).timestamp())
    ts1 = int(datetime(2024, 1, 8).timestamp())
    ts2 = int(datetime(2024, 1, 15).timestamp())
    return {
        "timelineData": [
            {"time": str(ts0), "value": "[80, 70]"},
            {"time": str(ts1), "value": "[85, 65]"},
            {"time": str(ts2), "value": "[90, 60]"},
        ]
    }


@pytest.fixture
def timeline_data_daily() -> dict:
    """Two entries 1 day apart."""
    ts0 = int(datetime(2024, 1, 1).timestamp())
    ts1 = int(datetime(2024, 1, 2).timestamp())
    return {
        "timelineData": [
            {"time": str(ts0), "value": "[50]"},
            {"time": str(ts1), "value": "[55]"},
        ]
    }


@pytest.fixture
def timeline_data_hourly() -> dict:
    """Two entries 1 hour apart."""
    ts0 = int(datetime(2024, 1, 1, 0, 0, 0).timestamp())
    ts1 = int(datetime(2024, 1, 1, 1, 0, 0).timestamp())
    return {
        "timelineData": [
            {"time": str(ts0), "value": "[40]"},
            {"time": str(ts1), "value": "[42]"},
        ]
    }
