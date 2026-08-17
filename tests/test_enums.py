"""Tests for trendflow.enums."""

from __future__ import annotations

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

    def test_past_hour_value(self) -> None:
        assert Timeframe.PAST_HOUR == "now 1-H"

    def test_past_4_hours_value(self) -> None:
        assert Timeframe.PAST_4_HOURS == "now 4-H"

    def test_past_month_value(self) -> None:
        assert Timeframe.PAST_MONTH == "today 1-m"

    def test_past_3_months_value(self) -> None:
        assert Timeframe.PAST_3_MONTHS == "today 3-m"

    def test_all_time_value(self) -> None:
        assert Timeframe.ALL_TIME == "all"

    def test_every_member_is_asserted_above(self) -> None:
        # A count alone breaks on every addition without saying what is wrong. Naming the
        # members means a new one fails here only if nobody wrote a test for its value.
        asserted = {
            "now 1-H",
            "now 4-H",
            "now 1-d",
            "now 7-d",
            "today 1-m",
            "today 3-m",
            "today 12-m",
            "today 5-y",
            "all",
        }
        assert {str(t) for t in Timeframe} == asserted

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
