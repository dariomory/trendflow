"""Tests for trendflow.enums."""

from __future__ import annotations

import pytest

from trendflow.enums import ExportFormat, Region, Resolution, Timeframe


class TestRegion:
    def test_worldwide_is_empty_string(self) -> None:
        assert Region.WORLDWIDE == ""

    def test_us_value(self) -> None:
        assert Region.US == "US"

    def test_all_non_worldwide_are_uppercase_two_letter(self) -> None:
        for region in Region:
            if region is not Region.WORLDWIDE:
                assert len(region.value) == 2
                assert region.value.isupper()

    def test_str_serialization(self) -> None:
        assert str(Region.GB) == "GB"
        assert str(Region.DE) == "DE"

    def test_all_expected_regions_present(self) -> None:
        codes = {r.value for r in Region}
        for expected in ("US", "GB", "DE", "FR", "IT", "ES", "CA", "AU", "JP", "IN", "BR", "MX"):
            assert expected in codes

    def test_comparable_to_string(self) -> None:
        assert Region.US == "US"
        assert "US" == Region.US

    def test_usable_in_f_string(self) -> None:
        assert f"geo={Region.US}" == "geo=US"
        assert f"geo={Region.WORLDWIDE}" == "geo="


class TestTimeframe:
    def test_past_day_value(self) -> None:
        assert Timeframe.PAST_DAY == "now 1-d"

    def test_past_week_value(self) -> None:
        assert Timeframe.PAST_WEEK == "now 7-d"

    def test_past_year_value(self) -> None:
        assert Timeframe.PAST_YEAR == "today 12-m"

    def test_past_5_years_value(self) -> None:
        assert Timeframe.PAST_5_YEARS == "today 5-y"

    def test_all_four_timeframes_exist(self) -> None:
        assert len(list(Timeframe)) == 4

    def test_str_serialization(self) -> None:
        assert str(Timeframe.PAST_DAY) == "now 1-d"


class TestResolution:
    def test_country_value(self) -> None:
        assert Resolution.COUNTRY == "COUNTRY"

    def test_region_value(self) -> None:
        assert Resolution.REGION == "REGION"

    def test_city_value(self) -> None:
        assert Resolution.CITY == "CITY"

    def test_all_three_exist(self) -> None:
        assert len(list(Resolution)) == 3

    def test_str_serialization(self) -> None:
        assert str(Resolution.CITY) == "CITY"


class TestExportFormat:
    def test_csv_value(self) -> None:
        assert ExportFormat.CSV == "csv"

    def test_json_value(self) -> None:
        assert ExportFormat.JSON == "json"

    def test_both_formats_exist(self) -> None:
        assert len(list(ExportFormat)) == 2

    def test_str_serialization(self) -> None:
        assert str(ExportFormat.CSV) == "csv"
        assert str(ExportFormat.JSON) == "json"
