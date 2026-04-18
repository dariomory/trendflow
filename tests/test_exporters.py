"""Tests for trendflow._exporters."""

from __future__ import annotations

import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from trendflow._exporters import (
    INTEREST_OVER_TIME_EXPORTERS,
    CsvInterestOverTimeExporter,
    JsonInterestOverTimeExporter,
    export_interest_over_time,
)
from trendflow.enums import ExportFormat
from trendflow.models import InterestOverTimeResult, TrendPoint


@pytest.fixture
def result_with_points() -> InterestOverTimeResult:
    return InterestOverTimeResult(
        keywords=["Python", "JavaScript"],
        granularity="weekly",
        points=[
            TrendPoint(date=datetime(2024, 1, 1), scores={"Python": 80, "JavaScript": 70}),
            TrendPoint(date=datetime(2024, 1, 8), scores={"Python": 85, "JavaScript": 65}),
        ],
    )


@pytest.fixture
def result_empty() -> InterestOverTimeResult:
    return InterestOverTimeResult(keywords=["Python"], granularity="unknown", points=[])


class TestCsvExporter:
    def test_creates_file(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_with_points, path)
            assert path.exists()
        finally:
            path.unlink(missing_ok=True)

    def test_csv_has_header_row(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_with_points, path)
            text = path.read_text(encoding="utf-8")
            first_line = text.splitlines()[0]
            assert "date" in first_line
            assert "Python" in first_line
            assert "JavaScript" in first_line
        finally:
            path.unlink(missing_ok=True)

    def test_csv_row_count_matches_points(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_with_points, path)
            with path.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            assert len(rows) == 2
        finally:
            path.unlink(missing_ok=True)

    def test_csv_values_present(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_with_points, path)
            text = path.read_text(encoding="utf-8")
            assert "80" in text
            assert "70" in text
        finally:
            path.unlink(missing_ok=True)

    def test_csv_empty_result_has_only_header(self, result_empty: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_empty, path)
            with path.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            assert rows == []
        finally:
            path.unlink(missing_ok=True)

    def test_csv_utf8_encoding(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            CsvInterestOverTimeExporter().export(result_with_points, path)
            # Should not raise
            path.read_text(encoding="utf-8")
        finally:
            path.unlink(missing_ok=True)


class TestJsonExporter:
    def test_creates_file(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            JsonInterestOverTimeExporter().export(result_with_points, path)
            assert path.exists()
        finally:
            path.unlink(missing_ok=True)

    def test_json_is_valid(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            JsonInterestOverTimeExporter().export(result_with_points, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, list)
        finally:
            path.unlink(missing_ok=True)

    def test_json_record_count_matches_points(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            JsonInterestOverTimeExporter().export(result_with_points, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == 2
        finally:
            path.unlink(missing_ok=True)

    def test_json_records_have_keyword_keys(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            JsonInterestOverTimeExporter().export(result_with_points, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "Python" in data[0]
            assert "JavaScript" in data[0]
        finally:
            path.unlink(missing_ok=True)

    def test_json_empty_result_is_empty_list(self, result_empty: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            JsonInterestOverTimeExporter().export(result_empty, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data == []
        finally:
            path.unlink(missing_ok=True)


class TestExportInterestOverTime:
    def test_dispatches_csv(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            export_interest_over_time(result_with_points, ExportFormat.CSV, path)
            text = path.read_text(encoding="utf-8")
            assert "Python" in text
        finally:
            path.unlink(missing_ok=True)

    def test_dispatches_json(self, result_with_points: InterestOverTimeResult) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            export_interest_over_time(result_with_points, ExportFormat.JSON, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, list)
        finally:
            path.unlink(missing_ok=True)

    def test_unsupported_format_raises_value_error(self, result_with_points: InterestOverTimeResult) -> None:
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_interest_over_time(result_with_points, "xml", Path("/tmp/out.xml"))  # type: ignore

    def test_exporters_registry_has_csv_and_json(self) -> None:
        assert ExportFormat.CSV in INTEREST_OVER_TIME_EXPORTERS
        assert ExportFormat.JSON in INTEREST_OVER_TIME_EXPORTERS

    def test_csv_exporter_type(self) -> None:
        assert isinstance(INTEREST_OVER_TIME_EXPORTERS[ExportFormat.CSV], CsvInterestOverTimeExporter)

    def test_json_exporter_type(self) -> None:
        assert isinstance(INTEREST_OVER_TIME_EXPORTERS[ExportFormat.JSON], JsonInterestOverTimeExporter)
