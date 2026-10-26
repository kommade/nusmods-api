"""Typed exceptions for the NUSMods API."""


class NUSModsError(Exception):
    """Base exception for all errors raised by the NUSMods wrapper."""


class NUSModsRequestError(NUSModsError):
    """Raised when a request cannot be completed."""


class NUSModsHTTPError(NUSModsError):
    """Raised when the API returns an unsuccessful HTTP status code."""

    def __init__(
        self,
        status_code: int,
        url: str,
        message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.message = message or f"NUSMods API returned HTTP {status_code}"
        super().__init__(f"{self.message}: {url}")


class NUSModsNotFoundError(NUSModsHTTPError):
    """Raised when the requested academic-year resource does not exist."""

    def __init__(self, url: str) -> None:
        super().__init__(404, url, "NUSMods resource not found")


class NUSModsInvalidResponseError(NUSModsError):
    """Raised when the API response cannot be decoded as JSON."""

    def __init__(self, url: str, message: str = "Invalid JSON response") -> None:
        self.url = url
        self.message = message
        super().__init__(f"{message}: {url}")
