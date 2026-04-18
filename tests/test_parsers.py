"""Tests for trendflow._parsers."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from trendflow._parsers import (
    _is_missing_value,
    _split_bracketed_ints,
    _to_int_or_none,
    infer_granularity,
    interest_by_region_rows,
    interest_by_region_to_result,
    interest_over_time_to_result,
    parse_rising_related,
    parse_top_related,
    related_queries_to_result,
    trending_result_from_titles,
    trending_titles_to_items,
)
from trendflow.enums import Resolution
from trendflow.models import (
    InterestByRegionResult,
    InterestOverTimeResult,
    RegionalInterestRow,
    RelatedQuery,
    RelatedResult,
    TrendingItem,
    TrendingResult,
)


class TestSplitBracketedInts:
    def test_bracketed_pair(self) -> None:
        assert _split_bracketed_ints("[80, 70]") == [80, 70]

    def test_single_value(self) -> None:
        assert _split_bracketed_ints("[42]") == [42]

    def test_no_brackets(self) -> None:
        assert _split_bracketed_ints("55") == [55]

    def test_extra_spaces(self) -> None:
        assert _split_bracketed_ints("[  10 ,  20  ]") == [10, 20]

    def test_empty_string(self) -> None:
        assert _split_bracketed_ints("") == []

    def test_empty_brackets(self) -> None:
        assert _split_bracketed_ints("[]") == []

    def test_three_values(self) -> None:
        assert _split_bracketed_ints("[1, 2, 3]") == [1, 2, 3]

    def test_integer_input(self) -> None:
        assert _split_bracketed_ints(99) == [99]


class TestIsMissingValue:
    def test_none_is_missing(self) -> None:
        assert _is_missing_value(None) is True

    def test_nan_is_missing(self) -> None:
        assert _is_missing_value(float("nan")) is True

    def test_math_nan_is_missing(self) -> None:
        assert _is_missing_value(math.nan) is True

    def test_zero_is_not_missing(self) -> None:
        assert _is_missing_value(0) is False

    def test_integer_not_missing(self) -> None:
        assert _is_missing_value(42) is False

    def test_string_not_missing(self) -> None:
        assert _is_missing_value("hello") is False

    def test_empty_string_not_missing(self) -> None:
        assert _is_missing_value("") is False

    def test_false_not_missing(self) -> None:
        assert _is_missing_value(False) is False

    def test_float_not_nan_not_missing(self) -> None:
        assert _is_missing_value(3.14) is False


class TestInferGranularity:
    def test_7_days_is_weekly(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = datetime(2024, 1, 8)
        assert infer_granularity(d0, d1) == "weekly"

    def test_6_days_is_weekly(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = datetime(2024, 1, 7)
        assert infer_granularity(d0, d1) == "weekly"

    def test_1_day_is_daily(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = datetime(2024, 1, 2)
        assert infer_granularity(d0, d1) == "daily"

    def test_5_days_is_daily(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = datetime(2024, 1, 6)
        assert infer_granularity(d0, d1) == "daily"

    def test_1_hour_is_hourly(self) -> None:
        d0 = datetime(2024, 1, 1, 0, 0)
        d1 = datetime(2024, 1, 1, 1, 0)
        assert infer_granularity(d0, d1) == "hourly"

    def test_30_minutes_is_hourly(self) -> None:
        d0 = datetime(2024, 1, 1, 0, 0)
        d1 = datetime(2024, 1, 1, 0, 30)
        assert infer_granularity(d0, d1) == "hourly"

    def test_boundary_exactly_6_days(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = d0 + timedelta(days=6)
        assert infer_granularity(d0, d1) == "weekly"

    def test_boundary_exactly_1_day(self) -> None:
        d0 = datetime(2024, 1, 1)
        d1 = d0 + timedelta(days=1)
        assert infer_granularity(d0, d1) == "daily"


class TestInterestOverTimeToResult:
    def test_empty_timeline(self) -> None:
        result = interest_over_time_to_result({}, ["Python"], "US")
        assert isinstance(result, InterestOverTimeResult)
        assert result.granularity == "unknown"
        assert result.points == []
        assert result.keywords == ["Python"]

    def test_none_timeline(self) -> None:
        result = interest_over_time_to_result({"timelineData": None}, ["Python"], "US")
        assert result.points == []

    def test_single_entry_unknown_granularity(self) -> None:
        ts = int(datetime(2024, 1, 1).timestamp())
        data = {"timelineData": [{"time": str(ts), "value": "[50]"}]}
        result = interest_over_time_to_result(data, ["Python"], "US")
        assert result.granularity == "unknown"
        assert len(result.points) == 1

    def test_weekly_granularity(self, timeline_data_weekly: dict) -> None:
        result = interest_over_time_to_result(timeline_data_weekly, ["Python", "JavaScript"], "US")
        assert result.granularity == "weekly"

    def test_daily_granularity(self, timeline_data_daily: dict) -> None:
        result = interest_over_time_to_result(timeline_data_daily, ["Python"], "US")
        assert result.granularity == "daily"

    def test_hourly_granularity(self, timeline_data_hourly: dict) -> None:
        result = interest_over_time_to_result(timeline_data_hourly, ["Python"], "US")
        assert result.granularity == "hourly"

    def test_single_geo_scores_keyed_by_keyword(self, timeline_data_weekly: dict) -> None:
        result = interest_over_time_to_result(
            timeline_data_weekly, ["Python", "JavaScript"], "US"
        )
        for point in result.points:
            assert "Python" in point.scores
            assert "JavaScript" in point.scores

    def test_single_geo_score_values(self, timeline_data_weekly: dict) -> None:
        result = interest_over_time_to_result(
            timeline_data_weekly, ["Python", "JavaScript"], "US"
        )
        assert result.points[0].scores["Python"] == 80
        assert result.points[0].scores["JavaScript"] == 70

    def test_multiple_geos_scores_keyed_with_pipe(self) -> None:
        ts0 = int(datetime(2024, 1, 1).timestamp())
        ts1 = int(datetime(2024, 1, 8).timestamp())
        data = {
            "timelineData": [
                {"time": str(ts0), "value": "[80, 60]"},
                {"time": str(ts1), "value": "[85, 65]"},
            ]
        }
        result = interest_over_time_to_result(data, ["Python"], ["US", "GB"])
        assert result.granularity == "weekly"
        assert "Python|US" in result.points[0].scores
        assert "Python|GB" in result.points[0].scores

    def test_multiple_geos_values(self) -> None:
        ts0 = int(datetime(2024, 1, 1).timestamp())
        ts1 = int(datetime(2024, 1, 8).timestamp())
        data = {
            "timelineData": [
                {"time": str(ts0), "value": "[80, 60]"},
                {"time": str(ts1), "value": "[85, 65]"},
            ]
        }
        result = interest_over_time_to_result(data, ["Python"], ["US", "GB"])
        assert result.points[0].scores["Python|US"] == 80
        assert result.points[0].scores["Python|GB"] == 60

    def test_point_count_matches_timeline(self, timeline_data_weekly: dict) -> None:
        result = interest_over_time_to_result(
            timeline_data_weekly, ["Python", "JavaScript"], "US"
        )
        assert len(result.points) == 3

    def test_keywords_preserved(self, timeline_data_weekly: dict) -> None:
        result = interest_over_time_to_result(
            timeline_data_weekly, ["Python", "JavaScript"], "US"
        )
        assert result.keywords == ["Python", "JavaScript"]

    def test_geo_as_list_with_single_element(self, timeline_data_daily: dict) -> None:
        result = interest_over_time_to_result(timeline_data_daily, ["Python"], ["US"])
        assert result.granularity == "daily"
        assert "Python" in result.points[0].scores

    def test_missing_value_field_treated_as_empty(self) -> None:
        ts = int(datetime(2024, 1, 1).timestamp())
        data = {"timelineData": [{"time": str(ts)}]}
        result = interest_over_time_to_result(data, ["Python"], "US")
        assert len(result.points) == 1
        assert result.points[0].scores == {}


class TestInterestByRegionRows:
    def test_basic_case(self) -> None:
        data = {
            "geoMapData": [
                {"geoName": "California", "value": "[90]"},
                {"geoName": "Texas", "value": "[70]"},
            ]
        }
        rows = interest_by_region_rows(data, "Python", ["Python"])
        assert len(rows) == 2
        assert rows[0].label == "California"
        assert rows[0].value == 90
        assert rows[1].label == "Texas"
        assert rows[1].value == 70

    def test_empty_geo_map_data(self) -> None:
        rows = interest_by_region_rows({"geoMapData": []}, "Python", ["Python"])
        assert rows == []

    def test_none_geo_map_data(self) -> None:
        rows = interest_by_region_rows({}, "Python", ["Python"])
        assert rows == []

    def test_keyword_not_in_kw_list_uses_index_zero(self) -> None:
        data = {
            "geoMapData": [{"geoName": "UK", "value": "[50, 80]"}]
        }
        rows = interest_by_region_rows(data, "Unknown", ["Python", "JS"])
        assert rows[0].value == 50

    def test_selects_correct_index_for_second_keyword(self) -> None:
        data = {
            "geoMapData": [{"geoName": "UK", "value": "[50, 80]"}]
        }
        rows = interest_by_region_rows(data, "JS", ["Python", "JS"])
        assert rows[0].value == 80

    def test_value_index_out_of_range_returns_zero(self) -> None:
        data = {
            "geoMapData": [{"geoName": "UK", "value": "[50]"}]
        }
        rows = interest_by_region_rows(data, "JS", ["Python", "JS"])
        assert rows[0].value == 0


class TestInterestByRegionToResult:
    def test_returns_correct_type(self) -> None:
        data = {"geoMapData": [{"geoName": "US", "value": "[100]"}]}
        result = interest_by_region_to_result(data, "Python", ["Python"], Resolution.COUNTRY)
        assert isinstance(result, InterestByRegionResult)

    def test_keyword_and_resolution_preserved(self) -> None:
        data = {"geoMapData": [{"geoName": "US", "value": "[100]"}]}
        result = interest_by_region_to_result(data, "Python", ["Python"], Resolution.REGION)
        assert result.keyword == "Python"
        assert result.resolution == Resolution.REGION


class TestTrendingTitlesToItems:
    def test_basic_mapping(self) -> None:
        items = trending_titles_to_items(["AI news", "Python 4"])
        assert len(items) == 2
        assert items[0].title == "AI news"
        assert items[1].title == "Python 4"

    def test_empty_traffic_and_articles(self) -> None:
        items = trending_titles_to_items(["test"])
        assert items[0].traffic == ""
        assert items[0].articles == []

    def test_empty_list(self) -> None:
        assert trending_titles_to_items([]) == []

    def test_non_string_titles_coerced(self) -> None:
        items = trending_titles_to_items([42, None])  # type: ignore[list-item]
        assert items[0].title == "42"
        assert items[1].title == "None"


class TestToIntOrNone:
    def test_none_returns_none(self) -> None:
        assert _to_int_or_none(None) is None

    def test_nan_returns_none(self) -> None:
        assert _to_int_or_none(float("nan")) is None

    def test_int_returns_int(self) -> None:
        assert _to_int_or_none(42) == 42
        assert _to_int_or_none(0) == 0

    def test_float_truncates(self) -> None:
        assert _to_int_or_none(3.9) == 3

    def test_bool_true(self) -> None:
        assert _to_int_or_none(True) == 1

    def test_bool_false(self) -> None:
        assert _to_int_or_none(False) == 0

    def test_string_int(self) -> None:
        assert _to_int_or_none("100") == 100

    def test_string_not_int_returns_none(self) -> None:
        assert _to_int_or_none("not_a_number") is None

    def test_list_returns_none(self) -> None:
        assert _to_int_or_none([1, 2]) is None


class TestParseTopRelated:
    def test_none_returns_empty(self) -> None:
        assert parse_top_related(None) == []

    def test_empty_list_returns_empty(self) -> None:
        assert parse_top_related([]) == []

    def test_basic_row(self) -> None:
        rows = [{"query": "python tutorial", "value": 100}]
        result = parse_top_related(rows)
        assert len(result) == 1
        assert result[0].term == "python tutorial"
        assert result[0].value == 100

    def test_missing_value_becomes_none(self) -> None:
        rows = [{"query": "python", "value": float("nan")}]
        result = parse_top_related(rows)
        assert result[0].value is None

    def test_none_value_becomes_none(self) -> None:
        rows = [{"query": "python", "value": None}]
        result = parse_top_related(rows)
        assert result[0].value is None

    def test_multiple_rows(self) -> None:
        rows = [
            {"query": "python tutorial", "value": 100},
            {"query": "python course", "value": 80},
        ]
        result = parse_top_related(rows)
        assert len(result) == 2
        assert result[1].term == "python course"
        assert result[1].value == 80

    def test_missing_query_key_defaults_to_empty_string(self) -> None:
        rows = [{"value": 50}]
        result = parse_top_related(rows)
        assert result[0].term == ""


class TestParseRisingRelated:
    def test_none_returns_empty(self) -> None:
        assert parse_rising_related(None) == []

    def test_empty_list_returns_empty(self) -> None:
        assert parse_rising_related([]) == []

    def test_uses_formatted_value(self) -> None:
        rows = [{"query": "python ai", "formattedValue": "+250%"}]
        result = parse_rising_related(rows)
        assert result[0].term == "python ai"
        assert result[0].breakout == "+250%"

    def test_falls_back_to_value_if_no_formatted_value(self) -> None:
        rows = [{"query": "python ai", "value": "Breakout"}]
        result = parse_rising_related(rows)
        assert result[0].breakout == "Breakout"

    def test_nan_breakout_becomes_none(self) -> None:
        rows = [{"query": "python ai", "formattedValue": float("nan")}]
        result = parse_rising_related(rows)
        assert result[0].breakout is None

    def test_none_breakout_becomes_none(self) -> None:
        rows = [{"query": "python ai", "formattedValue": None}]
        result = parse_rising_related(rows)
        assert result[0].breakout is None

    def test_breakout_coerced_to_string(self) -> None:
        rows = [{"query": "test", "formattedValue": 300}]
        result = parse_rising_related(rows)
        assert result[0].breakout == "300"

    def test_value_field_never_set_on_rising(self) -> None:
        rows = [{"query": "test", "formattedValue": "+100%"}]
        result = parse_rising_related(rows)
        assert result[0].value is None


class TestRelatedQueriesToResult:
    def test_empty_raw_returns_empty_result(self) -> None:
        result = related_queries_to_result({}, "Python")
        assert result.top == []
        assert result.rising == []

    def test_keyword_found(self) -> None:
        raw = {
            "Python": {
                "top": [{"query": "python tutorial", "value": 100}],
                "rising": [{"query": "python ai", "formattedValue": "+250%"}],
            }
        }
        result = related_queries_to_result(raw, "Python")
        assert len(result.top) == 1
        assert result.top[0].term == "python tutorial"
        assert len(result.rising) == 1
        assert result.rising[0].breakout == "+250%"

    def test_keyword_not_found_single_bucket_fallback(self) -> None:
        raw = {
            "OtherKW": {
                "top": [{"query": "something", "value": 50}],
                "rising": [],
            }
        }
        result = related_queries_to_result(raw, "Python")
        assert len(result.top) == 1
        assert result.top[0].term == "something"

    def test_keyword_not_found_multiple_buckets_returns_empty(self) -> None:
        raw = {
            "A": {"top": [{"query": "a", "value": 1}], "rising": []},
            "B": {"top": [{"query": "b", "value": 2}], "rising": []},
        }
        result = related_queries_to_result(raw, "Python")
        assert result.top == []
        assert result.rising == []

    def test_none_top_list(self) -> None:
        raw = {"Python": {"top": None, "rising": []}}
        result = related_queries_to_result(raw, "Python")
        assert result.top == []

    def test_none_rising_list(self) -> None:
        raw = {"Python": {"top": [], "rising": None}}
        result = related_queries_to_result(raw, "Python")
        assert result.rising == []

    def test_returns_related_result_type(self) -> None:
        raw = {"Python": {"top": [], "rising": []}}
        result = related_queries_to_result(raw, "Python")
        assert isinstance(result, RelatedResult)


class TestTrendingResultFromTitles:
    def test_returns_trending_result(self) -> None:
        result = trending_result_from_titles(["AI", "Python"])
        assert isinstance(result, TrendingResult)

    def test_correct_item_count(self) -> None:
        result = trending_result_from_titles(["A", "B", "C"])
        assert len(result.results) == 3

    def test_titles_mapped(self) -> None:
        result = trending_result_from_titles(["AI news"])
        assert result.results[0].title == "AI news"

    def test_empty_titles(self) -> None:
        result = trending_result_from_titles([])
        assert result.results == []
