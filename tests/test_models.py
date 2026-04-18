"""Tests for trendflow.models."""

from __future__ import annotations

import dataclasses
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from trendflow.enums import ExportFormat, Resolution
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


class TestTrendPoint:
    def test_construction(self) -> None:
        dt = datetime(2024, 1, 1)
        point = TrendPoint(date=dt, scores={"Python": 80})
        assert point.date == dt
        assert point.scores == {"Python": 80}

    def test_frozen(self) -> None:
        point = TrendPoint(date=datetime(2024, 1, 1), scores={"Python": 80})
        with pytest.raises(dataclasses.FrozenInstanceError):
            point.date = datetime(2024, 1, 2)  # type: ignore

    def test_equality(self) -> None:
        dt = datetime(2024, 1, 1)
        p1 = TrendPoint(date=dt, scores={"Python": 80})
        p2 = TrendPoint(date=dt, scores={"Python": 80})
        assert p1 == p2

    def test_multiple_keywords_in_scores(self) -> None:
        point = TrendPoint(
            date=datetime(2024, 1, 1),
            scores={"Python": 80, "JavaScript": 70, "Rust": 50},
        )
        assert point.scores["Python"] == 80
        assert point.scores["Rust"] == 50


class TestInterestOverTimeResult:
    def test_to_dataframe_empty(self, empty_iot_result: InterestOverTimeResult) -> None:
        df = empty_iot_result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "date" in df.columns
        assert "Python" in df.columns

    def test_to_dataframe_empty_has_keyword_columns(self) -> None:
        result = InterestOverTimeResult(keywords=["A", "B", "C"], granularity="unknown", points=[])
        df = result.to_dataframe()
        assert list(df.columns) == ["date", "A", "B", "C"]

    def test_to_dataframe_with_points(self, iot_result: InterestOverTimeResult) -> None:
        df = iot_result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "date" in df.columns
        assert "Python" in df.columns
        assert "JavaScript" in df.columns

    def test_to_dataframe_values(self, iot_result: InterestOverTimeResult) -> None:
        df = iot_result.to_dataframe()
        assert df["Python"].tolist() == [80, 85, 90]
        assert df["JavaScript"].tolist() == [70, 65, 60]

    def test_to_dataframe_date_column(self, iot_result: InterestOverTimeResult) -> None:
        df = iot_result.to_dataframe()
        assert df["date"].iloc[0] == datetime(2024, 1, 1)

    def test_frozen(self, iot_result: InterestOverTimeResult) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            iot_result.keywords = ["other"]  # type: ignore

    def test_export_csv(self, iot_result: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            iot_result.export(ExportFormat.CSV, path)
            content = path.read_text(encoding="utf-8")
            assert "Python" in content
            assert "JavaScript" in content
            assert "80" in content
        finally:
            path.unlink(missing_ok=True)

    def test_export_json(self, iot_result: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            iot_result.export(ExportFormat.JSON, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, list)
            assert len(data) == 3
        finally:
            path.unlink(missing_ok=True)

    def test_export_accepts_string_path(self, iot_result: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            iot_result.export(ExportFormat.CSV, path)
            assert Path(path).exists()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_single_keyword_dataframe(self) -> None:
        result = InterestOverTimeResult(
            keywords=["Rust"],
            granularity="daily",
            points=[TrendPoint(date=datetime(2024, 1, 1), scores={"Rust": 42})],
        )
        df = result.to_dataframe()
        assert list(df.columns) == ["date", "Rust"]
        assert df["Rust"].iloc[0] == 42


class TestRegionalInterestRow:
    def test_construction(self) -> None:
        row = RegionalInterestRow(label="California", value=90)
        assert row.label == "California"
        assert row.value == 90

    def test_frozen(self) -> None:
        row = RegionalInterestRow(label="California", value=90)
        with pytest.raises(dataclasses.FrozenInstanceError):
            row.value = 100  # type: ignore


class TestInterestByRegionResult:
    def test_construction(self, ibr_result: InterestByRegionResult) -> None:
        assert ibr_result.keyword == "Python"
        assert ibr_result.resolution == Resolution.REGION
        assert len(ibr_result.rows) == 2

    def test_frozen(self, ibr_result: InterestByRegionResult) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            ibr_result.keyword = "other"  # type: ignore

    def test_empty_rows(self) -> None:
        result = InterestByRegionResult(keyword="Python", resolution=Resolution.COUNTRY, rows=[])
        assert result.rows == []


class TestTrendingItem:
    def test_construction(self) -> None:
        item = TrendingItem(title="AI news", traffic="500K+", articles=[])
        assert item.title == "AI news"
        assert item.traffic == "500K+"
        assert item.articles == []

    def test_frozen(self) -> None:
        item = TrendingItem(title="AI news", traffic="500K+", articles=[])
        with pytest.raises(dataclasses.FrozenInstanceError):
            item.title = "other"  # type: ignore


class TestTrendingResult:
    def test_construction(self, trending_result: TrendingResult) -> None:
        assert len(trending_result.results) == 2
        assert trending_result.results[0].title == "AI tools"

    def test_empty(self) -> None:
        result = TrendingResult(results=[])
        assert result.results == []


class TestRelatedQuery:
    def test_defaults(self) -> None:
        q = RelatedQuery(term="python tutorial")
        assert q.value is None
        assert q.breakout is None

    def test_with_value(self) -> None:
        q = RelatedQuery(term="python tutorial", value=100)
        assert q.value == 100

    def test_with_breakout(self) -> None:
        q = RelatedQuery(term="python ai", breakout="+250%")
        assert q.breakout == "+250%"

    def test_frozen(self) -> None:
        q = RelatedQuery(term="python tutorial", value=100)
        with pytest.raises(dataclasses.FrozenInstanceError):
            q.term = "other"  # type: ignore


class TestRelatedResult:
    def test_construction(self, related_result: RelatedResult) -> None:
        assert len(related_result.top) == 1
        assert len(related_result.rising) == 1

    def test_empty(self) -> None:
        result = RelatedResult(top=[], rising=[])
        assert result.top == []
        assert result.rising == []
