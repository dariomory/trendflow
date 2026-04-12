from __future__ import annotations

from pathlib import Path
from typing import Protocol

from trendflow.enums import ExportFormat
from trendflow.models import InterestOverTimeResult


class InterestOverTimeExporter(Protocol):
    """Strategy for writing an :class:`~trendflow.models.InterestOverTimeResult` to disk."""

    def export(self, result: InterestOverTimeResult, path: Path) -> None:
        """Write ``result`` to ``path``."""
        ...


class CsvInterestOverTimeExporter:
    def export(self, result: InterestOverTimeResult, path: Path) -> None:
        result.to_dataframe().to_csv(path, index=False, encoding="utf-8")


class JsonInterestOverTimeExporter:
    def export(self, result: InterestOverTimeResult, path: Path) -> None:
        result.to_dataframe().to_json(path, orient="records", date_format="iso", indent=2)


INTEREST_OVER_TIME_EXPORTERS: dict[ExportFormat, InterestOverTimeExporter] = {
    ExportFormat.CSV: CsvInterestOverTimeExporter(),
    ExportFormat.JSON: JsonInterestOverTimeExporter(),
}


def export_interest_over_time(result: InterestOverTimeResult, fmt: ExportFormat, path: Path) -> None:
    """Dispatch export by format."""
    try:
        exporter = INTEREST_OVER_TIME_EXPORTERS[fmt]
    except KeyError as e:
        msg = f"Unsupported export format: {fmt!r}"
        raise ValueError(msg) from e
    exporter.export(result, path)
