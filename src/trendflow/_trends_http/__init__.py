"""
Google Trends internal JSON API client.

Split for maintainability: :mod:`~trendflow._trends_http.endpoints` (URLs),
:mod:`~trendflow._trends_http.exceptions`, :mod:`~trendflow._trends_http.transport`
(HTTP + cookies), :mod:`~trendflow._trends_http.session` (state + raw JSON).

Browser UIs may POST extra JSON to ``/api/explore``;
this library uses query-parameter POSTs for tokens.
"""

from trendflow._trends_http.endpoints import BASE_TRENDS_URL
from trendflow._trends_http.exceptions import ResponseError, TooManyRequestsError
from trendflow._trends_http.session import GoogleTrendsHttpSession

__all__ = [
    "BASE_TRENDS_URL",
    "GoogleTrendsHttpSession",
    "ResponseError",
    "TooManyRequestsError",
]
