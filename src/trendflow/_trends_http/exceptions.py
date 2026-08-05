from __future__ import annotations

from typing import Self

import httpx


class ResponseError(Exception):
    """The Trends endpoint returned a non-JSON or error response."""

    def __init__(self, message: str, response: httpx.Response) -> None:
        super().__init__(message)
        self.response = response

    @classmethod
    def from_response(cls, response: httpx.Response) -> Self:
        message = f"The request failed: Google returned a response with code {response.status_code}"
        return cls(message, response)


#: Where the rate-limit guidance lives. Deliberately a plain docs link, not a referral one.
RATE_LIMIT_DOCS_URL = "https://github.com/dariomory/trendflow#rate-limits"


class TooManyRequestsError(ResponseError):
    """HTTP 429 from Google Trends."""

    @classmethod
    def from_response(cls, response: httpx.Response) -> Self:
        message = (
            f"The request failed: Google returned a response with code {response.status_code}. "
            f"Google rate-limits by exit IP; see {RATE_LIMIT_DOCS_URL} for how to work around it."
        )
        return cls(message, response)
