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
    TrendingItem,
    TrendingResult,
    TrendPoint,
)


def _split_bracketed_ints(value: Any) -> list[int]:
    raw = str(value).replace("[", "").replace("]", "").split(",")
    return [int(x.strip()) for x in raw if x.strip()]


def _is_missing_value(val: Any) -> bool:
    if val is None:
        return True
    return isinstance(val, float) and math.isnan(val)


def infer_granularity(d0: datetime, d1: datetime) -> str:
    delta = d1 - d0
    days = delta.days
    if days >= 6:
        return "weekly"
    if days >= 1:
        return "daily"
    return "hourly"


def interest_over_time_to_result(
    default: Mapping[str, Any],
    keywords: list[str],
    geo: str | list[str],
) -> InterestOverTimeResult:
    """Build :class:`InterestOverTimeResult` from a widget ``default`` object (``timelineData``)."""
    geo_list = geo if isinstance(geo, list) else [geo]
    timeline = default.get("timelineData") or []
    if not timeline:
        return InterestOverTimeResult(keywords=keywords, granularity="unknown", points=[])

    if len(timeline) < 2:
        granularity = "unknown"
    else:
        t0 = float(timeline[0]["time"])
        t1 = float(timeline[1]["time"])
        granularity = infer_granularity(datetime.fromtimestamp(t0), datetime.fromtimestamp(t1))

    points: list[TrendPoint] = []
    for entry in timeline:
        ts = float(entry["time"])
        dt = datetime.fromtimestamp(ts)
        vals = _split_bracketed_ints(entry.get("value", ""))
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


def interest_by_region_rows(default: Mapping[str, Any], keyword: str, kw_list: list[str]) -> list[RegionalInterestRow]:
    """Rows from ``geoMapData`` for ``keyword`` (index in ``kw_list`` selects the value column)."""
    idx = kw_list.index(keyword) if keyword in kw_list else 0
    rows: list[RegionalInterestRow] = []
    for item in default.get("geoMapData") or []:
        label = str(item.get("geoName", ""))
        vals = _split_bracketed_ints(item.get("value", ""))
        val = vals[idx] if idx < len(vals) else 0
        rows.append(RegionalInterestRow(label=label, value=val))
    return rows


def interest_by_region_to_result(
    default: Mapping[str, Any],
    keyword: str,
    kw_list: list[str],
    resolution: Resolution,
) -> InterestByRegionResult:
    rows = interest_by_region_rows(default, keyword, kw_list)
    return InterestByRegionResult(keyword=keyword, resolution=resolution, rows=rows)


def trending_titles_to_items(titles: list[str]) -> list[TrendingItem]:
    """Map trending search title strings to :class:`TrendingItem` (no traffic/articles in this endpoint)."""
    return [TrendingItem(title=str(t), traffic="", articles=[]) for t in titles]


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


def parse_top_related(rows: list[dict[str, Any]] | None) -> list[RelatedQuery]:
    if not rows:
        return []
    out: list[RelatedQuery] = []
    for row in rows:
        term = str(row.get("query", ""))
        val = row.get("value")
        out.append(RelatedQuery(term=term, value=_to_int_or_none(val)))
    return out


def parse_rising_related(rows: list[dict[str, Any]] | None) -> list[RelatedQuery]:
    if not rows:
        return []
    out: list[RelatedQuery] = []
    for row in rows:
        term = str(row.get("query", ""))
        breakout = row.get("formattedValue", row.get("value"))
        if _is_missing_value(breakout):
            bstr = None
        else:
            bstr = str(breakout)
        out.append(RelatedQuery(term=term, breakout=bstr))
    return out


def related_queries_to_result(
    raw: dict[str, dict[str, list[dict[str, Any]] | None]],
    keyword: str,
) -> RelatedResult:
    """Pick the bucket for ``keyword``, or the sole bucket if only one series exists."""
    if not raw:
        return RelatedResult(top=[], rising=[])
    if keyword not in raw:
        part = next(iter(raw.values())) if len(raw) == 1 else None
        if part is None:
            return RelatedResult(top=[], rising=[])
    else:
        part = raw[keyword]
    top_rows = part.get("top")
    rising_rows = part.get("rising")
    return RelatedResult(
        top=parse_top_related(top_rows),
        rising=parse_rising_related(rising_rows),
    )


def trending_result_from_titles(titles: list[str]) -> TrendingResult:
    return TrendingResult(results=trending_titles_to_items(titles))
