from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from itertools import product
from typing import Any

from trendflow.enums import Resolution
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RegionalInterestRow,
    RelatedQuery,
    RelatedResult,
    TopicSuggestion,
    TrendingItem,
    TrendPoint,
)


def _split_bracketed_ints(value: Any) -> list[int]:
    raw = str(value).replace("[", "").replace("]", "").split(",")
    return [int(x.strip()) for x in raw if x.strip()]


def _is_missing_value(val: Any) -> bool:
    if val is None:
        return True
    return isinstance(val, float) and math.isnan(val)


def _rows(value: Any) -> list[Any]:
    """
    A list to iterate, whatever Google sent.

    Every parser below reads a positional structure that Google owns and can change without
    notice. Individual rows were already guarded; the containers were not, so a ``null`` where
    a list was expected raised out of the parser and became an error for the caller. Junk in,
    empty out -- never a throw.
    """
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    """A mapping to read, whatever Google sent. See :func:`_rows`."""
    return value if isinstance(value, Mapping) else {}


def _timestamp(entry: Any) -> float | None:
    """The epoch seconds on a timeline entry, or None if it does not carry a usable one."""
    raw = _mapping(entry).get("time")
    if not isinstance(raw, (str, int, float)) or isinstance(raw, bool):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def infer_granularity(d0: datetime, d1: datetime) -> str:
    delta = d1 - d0
    days = delta.days
    if days >= 6:
        return "weekly"
    if days >= 1:
        return "daily"
    return "hourly"


def interest_over_time_to_result(
    default: Any,
    keywords: list[str],
    geo: str | list[str],
) -> InterestOverTimeResult:
    """Build :class:`InterestOverTimeResult` from a widget ``default`` object (``timelineData``)."""
    geo_list = geo if isinstance(geo, list) else [geo]
    # Paired with the timestamp up front: an entry with no usable `time` cannot be placed on an
    # axis, and dropping it beats discarding the whole series over one malformed point.
    timeline = [
        (ts, entry) for entry in _rows(_mapping(default).get("timelineData")) if (ts := _timestamp(entry)) is not None
    ]
    if not timeline:
        return InterestOverTimeResult(keywords=keywords, granularity="unknown", points=[])

    if len(timeline) < 2:
        granularity = "unknown"
    else:
        granularity = infer_granularity(
            datetime.fromtimestamp(timeline[0][0]),
            datetime.fromtimestamp(timeline[1][0]),
        )

    points: list[TrendPoint] = []
    for ts, entry in timeline:
        dt = datetime.fromtimestamp(ts)
        vals = _split_bracketed_ints(_mapping(entry).get("value", ""))
        scores: dict[str, int] = {}
        for j, (kw, g) in enumerate(product(keywords, geo_list)):
            if j >= len(vals):
                break
            if len(geo_list) == 1:
                scores[kw] = vals[j]
            else:
                scores[f"{kw}|{g}"] = vals[j]
        points.append(TrendPoint(date=dt, scores=scores))

    return InterestOverTimeResult(keywords=keywords, granularity=granularity, points=points)


def interest_by_region_rows(default: Any, keyword: str, kw_list: list[str]) -> list[RegionalInterestRow]:
    """Rows from ``geoMapData`` for ``keyword`` (index in ``kw_list`` selects the value column)."""
    idx = kw_list.index(keyword) if keyword in kw_list else 0
    rows: list[RegionalInterestRow] = []
    for item in _rows(_mapping(default).get("geoMapData")):
        label = str(_mapping(item).get("geoName", ""))
        vals = _split_bracketed_ints(_mapping(item).get("value", ""))
        val = vals[idx] if idx < len(vals) else 0
        rows.append(RegionalInterestRow(label=label, value=val))
    return rows


def interest_by_region_to_result(
    default: Any,
    keyword: str,
    kw_list: list[str],
    resolution: Resolution,
) -> InterestByRegionResult:
    rows = interest_by_region_rows(default, keyword, kw_list)
    return InterestByRegionResult(keyword=keyword, resolution=resolution, rows=rows)


def _format_growth(growth: int | None) -> str:
    if growth is None:
        return ""
    sign = "+" if growth >= 0 else "-"
    return f"{sign}{abs(growth):,}%"


def trending_rows_to_items(rows: Any) -> list[TrendingItem]:
    """Map ``[term, growth_percent, volume_index]`` rows from the trending RPC to items."""
    items: list[TrendingItem] = []
    for row in _rows(rows):
        if not isinstance(row, list) or not row:
            continue
        growth = _to_int_or_none(row[1]) if len(row) > 1 else None
        items.append(
            TrendingItem(
                title=str(row[0]),
                traffic=_format_growth(growth),
                # The RPC carries neither articles nor a start time; RSS supplies those.
                articles=[],
                growth=growth,
                volume=_to_int_or_none(row[2]) if len(row) > 2 else None,
                started_at=None,
            ),
        )
    return items


def suggestion_rows_to_topics(rows: Any) -> list[TopicSuggestion]:
    """Map ``[mid, title, type, ...]`` rows from the suggestions RPC to topics."""
    out: list[TopicSuggestion] = []
    for row in _rows(rows):
        if not isinstance(row, list) or not row or not isinstance(row[0], str):
            continue
        raw_type = row[2] if len(row) > 2 else None
        topic_type = raw_type if isinstance(raw_type, str) and raw_type else None
        out.append(
            TopicSuggestion(
                mid=row[0],
                title=str(row[1]) if len(row) > 1 and row[1] is not None else "",
                type=topic_type,
            ),
        )
    return out


def _to_int_or_none(val: Any) -> int | None:
    if _is_missing_value(val):
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def parse_top_related(rows: Any) -> list[RelatedQuery]:
    out: list[RelatedQuery] = []
    for row in _rows(rows):
        term = str(_mapping(row).get("query", ""))
        val = _mapping(row).get("value")
        out.append(RelatedQuery(term=term, value=_to_int_or_none(val)))
    return out


def parse_rising_related(rows: Any) -> list[RelatedQuery]:
    out: list[RelatedQuery] = []
    for row in _rows(rows):
        cells = _mapping(row)
        term = str(cells.get("query", ""))
        breakout = cells.get("formattedValue", cells.get("value"))
        if _is_missing_value(breakout):
            bstr = None
        else:
            bstr = str(breakout)
        out.append(RelatedQuery(term=term, breakout=bstr))
    return out


def related_queries_to_result(
    raw: Any,
    keyword: str,
) -> RelatedResult:
    """Pick the bucket for ``keyword``, or the sole bucket if only one series exists."""
    buckets = _mapping(raw)
    if not buckets:
        return RelatedResult(top=[], rising=[])
    if keyword in buckets:
        part = buckets[keyword]
    elif len(buckets) == 1:
        part = next(iter(buckets.values()))
    else:
        return RelatedResult(top=[], rising=[])
    cells = _mapping(part)
    return RelatedResult(
        top=parse_top_related(cells.get("top")),
        rising=parse_rising_related(cells.get("rising")),
    )
