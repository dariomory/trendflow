from __future__ import annotations

from typing import Final

BASE_TRENDS_URL: Final[str] = "https://trends.google.com/trends"

EXPLORE: Final[str] = f"{BASE_TRENDS_URL}/api/explore"
INTEREST_OVER_TIME: Final[str] = f"{BASE_TRENDS_URL}/api/widgetdata/multiline"
MULTIRANGE_INTEREST_OVER_TIME: Final[str] = f"{BASE_TRENDS_URL}/api/widgetdata/multirange"
INTEREST_BY_REGION: Final[str] = f"{BASE_TRENDS_URL}/api/widgetdata/comparedgeo"
RELATED_QUERIES: Final[str] = f"{BASE_TRENDS_URL}/api/widgetdata/relatedsearches"
TRENDING_SEARCHES: Final[str] = f"{BASE_TRENDS_URL}/hottrends/visualize/internal/data"
TOP_CHARTS: Final[str] = f"{BASE_TRENDS_URL}/api/topcharts"
AUTOCOMPLETE_PREFIX: Final[str] = f"{BASE_TRENDS_URL}/api/autocomplete/"
GEO_PICKER: Final[str] = f"{BASE_TRENDS_URL}/api/explore/pickers/geo"
CATEGORY_PICKER: Final[str] = f"{BASE_TRENDS_URL}/api/explore/pickers/category"
TODAY_SEARCHES: Final[str] = f"{BASE_TRENDS_URL}/api/dailytrends"
REALTIME_TRENDING: Final[str] = f"{BASE_TRENDS_URL}/api/realtimetrends"

HTTP_TOO_MANY_REQUESTS: Final[int] = 429
