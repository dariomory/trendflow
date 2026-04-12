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
    """Time ranges accepted by Google Trends."""

    PAST_DAY = "now 1-d"
    PAST_WEEK = "now 7-d"
    PAST_YEAR = "today 12-m"
    PAST_5_YEARS = "today 5-y"


class Resolution(StrEnum):
    """Granularity for regional interest breakdowns."""

    COUNTRY = "COUNTRY"
    REGION = "REGION"
    CITY = "CITY"


class ExportFormat(StrEnum):
    """Supported export targets for tabular trend data."""

    CSV = "csv"
    JSON = "json"
