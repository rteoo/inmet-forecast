"""Public exceptions; response bodies are deliberately excluded from messages."""


class InmetError(Exception):
    """Base class for INMET transport and response failures."""


class InmetHTTPError(InmetError):
    """The API returned an unsuccessful HTTP status."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"INMET returned HTTP {status}.")


class InmetNetworkError(InmetError):
    """The API could not be reached or the connection timed out."""


class InmetResponseError(InmetError):
    """The API response was empty, malformed, or incompatible."""
