from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trendflow.enums import ExportFormat, Resolution


@dataclass(frozen=True)
class TrendPoint:
    """One timestamp in an interest-over-time series."""

    date: datetime
    scores: dict[str, int]


@dataclass(frozen=True)
class InterestOverTimeResult:
    """Interest over time for one or more keywords."""

    keywords: list[str]
    granularity: str
    points: list[TrendPoint]

    def to_dataframe(self) -> pd.DataFrame:
        """Build a pandas DataFrame with a `date` column and one column per keyword."""
        if not self.points:
            return pd.DataFrame(columns=["date", *self.keywords])
        rows: list[dict[str, Any]] = []
        for p in self.points:
            rows.append({"date": p.date, **p.scores})
        return pd.DataFrame(rows)

    def export(self, fmt: ExportFormat, path: str | Path) -> None:
        """Write results to CSV or JSON (UTF-8) via :mod:`trendflow._exporters`."""
        from trendflow._exporters import export_interest_over_time

        export_interest_over_time(self, fmt, Path(path))


@dataclass(frozen=True)
class RegionalInterestRow:
    """One region row from interest-by-region."""

    label: str
    value: int


@dataclass(frozen=True)
class InterestByRegionResult:
    """Regional popularity for a single keyword."""

    keyword: str
    resolution: Resolution
    rows: list[RegionalInterestRow]


@dataclass(frozen=True)
class TrendingItem:
    """A single trending search entry."""

    title: str
    traffic: str
    articles: list[str]
    #: Percentage increase in searches over the window, e.g. ``3950`` for a 3,950% rise.
    growth: int | None = None
    #: Relative search volume for the term, on Google's own 0-100 style scale.
    volume: int | None = None


@dataclass(frozen=True)
class TrendingResult:
    """Current trending searches for a region."""

    results: list[TrendingItem]


@dataclass(frozen=True)
class TopicSuggestion:
    """
    An entity Google recognises, as returned by search suggestions.

    ``mid`` is the identifier to pass as a keyword to query the **topic** rather than the
    literal phrase -- a topic aggregates every spelling and translation of the same concept.
    """

    #: Freebase-style entity id, e.g. ``"/m/0mkz"``. Pass this as a keyword.
    mid: str
    #: Display name, e.g. ``"Artificial intelligence"``.
    title: str
    #: Disambiguating descriptor, e.g. ``"Professional field"``. ``None`` when Google omits it.
    type: str | None = None


@dataclass(frozen=True)
class RelatedQuery:
    """A top or rising related query."""

    term: str
    value: int | None = None
    breakout: str | None = None


@dataclass(frozen=True)
class RelatedResult:
    """Related queries for a seed keyword."""

    top: list[RelatedQuery]
    rising: list[RelatedQuery]
