from enum import StrEnum


class Region(StrEnum):
    """ISO-style geo codes for Google Trends (`hl` / `geo`). Empty string is worldwide."""

    WORLDWIDE = ""
    US = "US"
    GB = "GB"
    DE = "DE"
    FR = "FR"
    IT = "IT"
    ES = "ES"
    CA = "CA"
    AU = "AU"
    JP = "JP"
    IN = "IN"
    BR = "BR"
    MX = "MX"
    NL = "NL"
    SE = "SE"
    PL = "PL"
    TR = "TR"


class Timeframe(StrEnum):
    """
    Time ranges accepted by Google Trends.

    Named values for the presets. A custom range is a plain string of two ISO dates,
    ``"2023-01-01 2023-06-30"``, and every query method accepts one in place of a member.

    The range chosen also decides the granularity Google returns: the hourly ranges come back
    in minutes, the daily ones hourly, and ``ALL_TIME`` monthly. Ask for five years and you
    cannot see a spike that lasted an afternoon.
    """

    PAST_HOUR = "now 1-H"
    PAST_4_HOURS = "now 4-H"
    PAST_DAY = "now 1-d"
    PAST_WEEK = "now 7-d"
    PAST_MONTH = "today 1-m"
    PAST_3_MONTHS = "today 3-m"
    PAST_YEAR = "today 12-m"
    PAST_5_YEARS = "today 5-y"
    ALL_TIME = "all"


class SearchProperty(StrEnum):
    """
    Which Google surface to measure.

    These are separate indexes, not filters over one dataset, so the same term can look very
    different across them -- a term may be quiet on web search and busy on YouTube. Values are
    only comparable within a single property.
    """

    WEB = ""
    IMAGES = "images"
    NEWS = "news"
    YOUTUBE = "youtube"
    SHOPPING = "froogle"


class Resolution(StrEnum):
    """Granularity for regional interest breakdowns."""

    COUNTRY = "COUNTRY"
    REGION = "REGION"
    CITY = "CITY"


class ExportFormat(StrEnum):
    """Supported export targets for tabular trend data."""

    CSV = "csv"
    JSON = "json"
