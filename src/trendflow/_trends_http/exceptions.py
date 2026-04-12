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


class TooManyRequestsError(ResponseError):
    """HTTP 429 from Google Trends."""
