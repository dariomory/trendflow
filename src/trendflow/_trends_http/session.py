from __future__ import annotations

import json
import logging
from collections.abc import Mapping, MutableMapping, Sequence
from itertools import product
from typing import Any, Literal
from urllib.parse import quote

import httpx

from trendflow._trends_http import endpoints as ep
from trendflow._trends_http.transport import TrendsJsonTransport

logger = logging.getLogger(__name__)

Gprop = Literal["", "images", "news", "youtube", "froogle"]


def _normalize_proxies(proxies: str | Sequence[str]) -> list[str]:
    if isinstance(proxies, str):
        return [proxies] if proxies else []
    return list(proxies)


def _primary_geo(geo: str | list[str]) -> str:
    if isinstance(geo, str):
        return geo
    if not geo:
        return ""
    return str(geo[0])


class GoogleTrendsHttpSession:
    """
    Stateful client for Google Trends internal APIs (explore + widgetdata).

    Composes :class:`TrendsJsonTransport` for HTTP; this class holds comparison
    state and returns raw JSON for callers to parse (e.g. :mod:`trendflow._parsers`).
    """

    def __init__(
        self,
        hl: str = "en-US",
        tz: int = 360,
        geo: str = "",
        timeout: httpx.Timeout | tuple[float, float] | float = (2, 5),
        proxies: str | Sequence[str] = "",
        retries: int = 0,
        backoff_factor: float = 0,
        requests_args: Mapping[str, Any] | None = None,
    ) -> None:
        self.tz = tz
        self.hl = hl
        self.geo: str | list[str] = geo
        self.kw_list: list[str] = []
        self.timeout = timeout
        self.proxies = _normalize_proxies(proxies)
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.requests_args: dict[str, Any] = dict(requests_args or {})
        self.results: Any = None

        headers: MutableMapping[str, str] = {
            "accept": "application/json, text/plain, */*",
            "accept-language": self.hl,
            "origin": "https://trends.google.com",
            "referer": f"{ep.BASE_TRENDS_URL}/explore",
        }
        headers.update(self.requests_args.pop("headers", {}))

        self._http = TrendsJsonTransport(
            hl=self.hl,
            tz=self.tz,
            timeout=self.timeout,
            headers=headers,
            extra_client_args=self.requests_args,
            proxy_urls=self.proxies,
            retries=self.retries,
        )

        self.token_payload: dict[str, Any] = {}
        self.interest_over_time_widget: dict[str, Any] = {}
        self.interest_by_region_widget: dict[str, Any] = {}
        self.related_topics_widget_list: list[dict[str, Any]] = []
        self.related_queries_widget_list: list[dict[str, Any]] = []

    @property
    def proxy_index(self) -> int:
        return self._http._proxy_index

    @property
    def cookies(self) -> dict[str, str]:
        return self._http.cookies

    @cookies.setter
    def cookies(self, value: dict[str, str]) -> None:
        self._http.cookies = value

    def _get_data(self, url: str, method: Literal["get", "post"] = "get", trim_chars: int = 0, **kwargs: Any) -> Any:
        return self._http.request_json(url, method, trim_chars=trim_chars, **kwargs)

    def build_payload(
        self,
        kw_list: list[str],
        cat: int = 0,
        timeframe: str | list[str] = "today 5-y",
        geo: str = "",
        gprop: Gprop = "",
    ) -> None:
        allowed: tuple[str, ...] = ("", "images", "news", "youtube", "froogle")
        if gprop not in allowed:
            raise ValueError(
                "gprop must be empty (web), images, news, youtube, or froogle",
            )
        self.kw_list = kw_list
        self.geo = geo or self.geo
        self.token_payload = {
            "hl": self.hl,
            "tz": self.tz,
            "req": {"comparisonItem": [], "category": cat, "property": gprop},
        }

        if not isinstance(self.geo, list):
            self.geo = [self.geo]

        if isinstance(timeframe, list):
            for index, (kw, geo_item) in enumerate(product(self.kw_list, self.geo)):
                payload = {"keyword": kw, "time": timeframe[index], "geo": geo_item}
                self.token_payload["req"]["comparisonItem"].append(payload)
        else:
            for kw, geo_item in product(self.kw_list, self.geo):
                payload = {"keyword": kw, "time": timeframe, "geo": geo_item}
                self.token_payload["req"]["comparisonItem"].append(payload)

        self.token_payload["req"] = json.dumps(self.token_payload["req"])
        self._tokens()

    def _tokens(self) -> None:
        widget_dicts = self._get_data(
            url=ep.EXPLORE,
            method="post",
            params=self.token_payload,
            trim_chars=4,
        )["widgets"]
        first_region_token = True
        self.related_queries_widget_list.clear()
        self.related_topics_widget_list.clear()
        for widget in widget_dicts:
            if widget["id"] == "TIMESERIES":
                self.interest_over_time_widget = widget
            if widget["id"] == "GEO_MAP" and first_region_token:
                self.interest_by_region_widget = widget
                first_region_token = False
            if "RELATED_TOPICS" in widget["id"]:
                self.related_topics_widget_list.append(widget)
            if "RELATED_QUERIES" in widget["id"]:
                self.related_queries_widget_list.append(widget)

    def interest_over_time(self) -> dict[str, Any]:
        """Return the raw ``default`` object from the interest-over-time widget response."""
        over_time_payload = {
            "req": json.dumps(self.interest_over_time_widget["request"]),
            "token": self.interest_over_time_widget["token"],
            "tz": self.tz,
        }
        req_json = self._get_data(
            url=ep.INTEREST_OVER_TIME,
            method="get",
            trim_chars=5,
            params=over_time_payload,
        )
        return req_json["default"]

    def multirange_interest_over_time(self) -> dict[str, Any]:
        """Return the raw ``default`` object from the multirange interest-over-time response."""
        over_time_payload = {
            "req": json.dumps(self.interest_over_time_widget["request"]),
            "token": self.interest_over_time_widget["token"],
            "tz": self.tz,
        }
        req_json = self._get_data(
            url=ep.MULTIRANGE_INTEREST_OVER_TIME,
            method="get",
            trim_chars=5,
            params=over_time_payload,
        )
        return req_json["default"]

    def interest_by_region(
        self,
        resolution: str = "COUNTRY",
        inc_low_vol: bool = False,
        inc_geo_code: bool = False,
    ) -> dict[str, Any]:
        """Return the raw ``default`` object from the interest-by-region response."""
        g = _primary_geo(self.geo)
        if g == "":
            self.interest_by_region_widget["request"]["resolution"] = resolution
        elif g == "US" and resolution in ("DMA", "CITY", "REGION"):
            self.interest_by_region_widget["request"]["resolution"] = resolution

        self.interest_by_region_widget["request"]["includeLowSearchVolumeGeos"] = inc_low_vol

        region_payload = {
            "req": json.dumps(self.interest_by_region_widget["request"]),
            "token": self.interest_by_region_widget["token"],
            "tz": self.tz,
        }
        req_json = self._get_data(
            url=ep.INTEREST_BY_REGION,
            method="get",
            trim_chars=5,
            params=region_payload,
        )
        default = req_json["default"]
        if inc_geo_code:
            if "geoMapData" in default and default["geoMapData"]:
                first = default["geoMapData"][0]
                if "geoCode" not in first and "coordinates" not in first:
                    logger.warning("Could not find geo_code column; skipping")
        return default

    def related_topics(self) -> dict[str, dict[str, list[dict[str, Any]] | None]]:
        """Per-keyword related topics: ``top`` / ``rising`` lists of ranked-keyword dicts."""
        result_dict: dict[str, dict[str, list[dict[str, Any]] | None]] = {}
        for request_json in self.related_topics_widget_list:
            try:
                kw = request_json["request"]["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
            except KeyError:
                kw = ""
            related_payload = {
                "req": json.dumps(request_json["request"]),
                "token": request_json["token"],
                "tz": self.tz,
            }
            req_json = self._get_data(
                url=ep.RELATED_QUERIES,
                method="get",
                trim_chars=5,
                params=related_payload,
            )
            try:
                top_list = req_json["default"]["rankedList"][0]["rankedKeyword"]
            except KeyError:
                top_list = None
            try:
                rising_list = req_json["default"]["rankedList"][1]["rankedKeyword"]
            except KeyError:
                rising_list = None
            result_dict[kw] = {"rising": rising_list, "top": top_list}
        return result_dict

    def related_queries(self) -> dict[str, dict[str, list[dict[str, Any]] | None]]:
        """Per-keyword related queries: ``top`` / ``rising`` lists of ranked-keyword dicts."""
        result_dict: dict[str, dict[str, list[dict[str, Any]] | None]] = {}
        for request_json in self.related_queries_widget_list:
            try:
                kw = request_json["request"]["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
            except KeyError:
                kw = ""
            related_payload = {
                "req": json.dumps(request_json["request"]),
                "token": request_json["token"],
                "tz": self.tz,
            }
            req_json = self._get_data(
                url=ep.RELATED_QUERIES,
                method="get",
                trim_chars=5,
                params=related_payload,
            )
            try:
                top_list = list(req_json["default"]["rankedList"][0]["rankedKeyword"])
            except KeyError:
                top_list = None
            try:
                rising_list = list(req_json["default"]["rankedList"][1]["rankedKeyword"])
            except KeyError:
                rising_list = None
            result_dict[kw] = {"top": top_list, "rising": rising_list}
        return result_dict

    def trending_searches(self, pn: str = "united_states") -> list[str]:
        """Trending search titles for the given property namespace key (e.g. ``united_states``)."""
        req_json = self._get_data(url=ep.TRENDING_SEARCHES, method="get")[pn]
        return list(req_json)

    def today_searches(self, pn: str = "US") -> list[str]:
        """Today's search titles for ``pn`` (country code)."""
        forms = {"ns": 15, "geo": pn, "tz": "-180", "hl": self.hl}
        req_json = self._get_data(
            url=ep.TODAY_SEARCHES,
            method="get",
            trim_chars=5,
            params=forms,
            **self.requests_args,
        )["default"]["trendingSearchesDays"][0]["trendingSearches"]
        return [str(trend["title"]) for trend in req_json]

    def realtime_trending_searches(
        self,
        pn: str = "US",
        cat: str = "all",
        count: int = 300,
    ) -> list[dict[str, Any]]:
        ri_value = min(300, count)
        rs_value = min(200, count - 1) if count < 200 else 200
        forms = {
            "ns": 15,
            "geo": pn,
            "tz": "300",
            "hl": self.hl,
            "cat": cat,
            "fi": "0",
            "fs": "0",
            "ri": ri_value,
            "rs": rs_value,
            "sort": 0,
        }
        req_json = self._get_data(
            url=ep.REALTIME_TRENDING,
            method="get",
            trim_chars=5,
            params=forms,
        )["storySummaries"]["trendingStories"]
        wanted_keys = ("entityNames", "title")
        return [{k: ts[k] for k in ts if k in wanted_keys} for ts in req_json]

    def top_charts(
        self,
        date: int | str,
        hl: str = "en-US",
        tz: int = 300,
        geo: str = "GLOBAL",
    ) -> list[dict[str, Any]] | None:
        try:
            year = int(date)
        except (TypeError, ValueError) as e:
            raise ValueError("The date must be a year with format YYYY.") from e
        chart_payload = {"hl": hl, "tz": tz, "date": year, "geo": geo, "isMobile": False}
        req_json = self._get_data(
            url=ep.TOP_CHARTS,
            method="get",
            trim_chars=5,
            params=chart_payload,
        )
        try:
            return list(req_json["topCharts"][0]["listItems"])
        except IndexError:
            return None

    def suggestions(self, keyword: str) -> Any:
        kw_param = quote(keyword)
        parameters = {"hl": self.hl}
        return self._get_data(
            url=ep.AUTOCOMPLETE_PREFIX + kw_param,
            params=parameters,
            method="get",
            trim_chars=5,
        )["default"]["topics"]

    def geo_picker(self) -> Any:
        return self._get_data(
            url=ep.GEO_PICKER,
            params={"hl": self.hl, "tz": self.tz},
            method="get",
            trim_chars=5,
        )

    def categories(self) -> Any:
        return self._get_data(
            url=ep.CATEGORY_PICKER,
            params={"hl": self.hl, "tz": self.tz},
            method="get",
            trim_chars=5,
        )
