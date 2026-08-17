"""
The contract every parser owes its caller: junk in, empty out, never a throw.

Google owns these response shapes and changes them without notice — it has retired whole
endpoints in this product before. A parser that raises on an unexpected shape turns a partial
degradation into a hard failure for the caller, and in the hosted service into a tool error for
a paying customer. Returning nothing is honest; raising is not.

These are deliberately blunt: every parser, against every shape of nonsense, asserting only
that it returns the empty form. A new parser without an entry here is the gap worth catching.
"""

from __future__ import annotations

from typing import Any

import pytest

from trendflow import _parsers as parsers
from trendflow.enums import Resolution
from trendflow.models import InterestByRegionResult, InterestOverTimeResult, RelatedResult

#: Values Google could plausibly put where a list or object is expected. `None` is included
#: because a JSON `null` deserialises to it, which is the most likely drift of all.
JUNK: list[Any] = [
    None,
    0,
    "",
    "a string",
    [],
    {},
    [None],
    [[]],
    [{}],
    [0],
    {"unexpected": None},
    {"timelineData": None},
    {"geoMapData": "not a list"},
    [{"no": "expected keys"}],
    [["one element"]],
]


@pytest.mark.parametrize("junk", JUNK)
class TestRowParsers:
    """
    The contract here is "returns a list, never throws" rather than "always empty".

    Some entries above are not junk to every parser — `[["one element"]]` is a valid minimal
    suggestion row, and producing a result from it is correct. Asserting emptiness would be
    asserting that these parsers discard usable data.
    """

    def test_trending_rows(self, junk: Any) -> None:
        assert isinstance(parsers.trending_rows_to_items(junk), list)

    def test_suggestion_rows(self, junk: Any) -> None:
        assert isinstance(parsers.suggestion_rows_to_topics(junk), list)

    def test_top_related(self, junk: Any) -> None:
        assert isinstance(parsers.parse_top_related(junk), list)

    def test_rising_related(self, junk: Any) -> None:
        assert isinstance(parsers.parse_rising_related(junk), list)

    def test_wholly_unusable_input_yields_nothing(self, junk: Any) -> None:
        # Narrower claim, on the shapes that genuinely carry no rows at all.
        if junk in (None, 0, "", [], {}):
            assert parsers.trending_rows_to_items(junk) == []
            assert parsers.suggestion_rows_to_topics(junk) == []


@pytest.mark.parametrize("junk", JUNK)
class TestResultParsers:
    def test_interest_over_time(self, junk: Any) -> None:
        result = parsers.interest_over_time_to_result(junk, ["kw"], "US")
        assert isinstance(result, InterestOverTimeResult)
        assert result.points == []
        assert result.granularity == "unknown"

    def test_interest_by_region_rows(self, junk: Any) -> None:
        assert parsers.interest_by_region_rows(junk, "kw", ["kw"]) == []

    def test_interest_by_region_result(self, junk: Any) -> None:
        result = parsers.interest_by_region_to_result(junk, "kw", ["kw"], Resolution.COUNTRY)
        assert isinstance(result, InterestByRegionResult)
        assert result.rows == []

    def test_related_queries(self, junk: Any) -> None:
        result = parsers.related_queries_to_result(junk, "kw")
        assert isinstance(result, RelatedResult)


class TestPartialShapes:
    """Half-valid payloads — the realistic drift, rather than wholesale nonsense."""

    def test_timeline_entry_without_a_timestamp_is_skipped(self) -> None:
        # A point with no usable `time` cannot be placed on an axis, so it is dropped rather
        # than crashing the whole series.
        raw = {
            "timelineData": [
                {"time": "1700000000", "value": "[50]"},
                {"value": "[60]"},
                {"time": None, "value": "[70]"},
                {"time": "1700604800", "value": "[80]"},
            ],
        }
        result = parsers.interest_over_time_to_result(raw, ["kw"], "US")
        assert [p.scores["kw"] for p in result.points] == [50, 80]

    def test_region_rows_survive_a_missing_label(self) -> None:
        raw = {"geoMapData": [{"value": "[42]"}, None, {"geoName": "Texas", "value": "[7]"}]}
        rows = parsers.interest_by_region_rows(raw, "kw", ["kw"])
        assert [(r.label, r.value) for r in rows] == [("", 42), ("", 0), ("Texas", 7)]

    def test_related_result_picks_the_sole_bucket(self) -> None:
        raw = {"other keyword": {"top": [{"query": "a", "value": 1}], "rising": None}}
        result = parsers.related_queries_to_result(raw, "kw")
        assert [q.term for q in result.top] == ["a"]
        assert result.rising == []

    def test_related_result_declines_to_guess_between_buckets(self) -> None:
        # Two buckets and neither matches: picking one would attribute another term's data.
        raw = {"a": {"top": [{"query": "x"}]}, "b": {"top": [{"query": "y"}]}}
        assert parsers.related_queries_to_result(raw, "kw").top == []
