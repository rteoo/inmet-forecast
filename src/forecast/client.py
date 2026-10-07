"""Small HTTPS client built entirely on the Python standard library."""

import json
import math
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import InmetHTTPError, InmetNetworkError, InmetResponseError
from .forecast import municipality_code, validate_forecast

FORECAST_BASE_URL = "https://apiprevmet3.inmet.gov.br"
# ceiling: 8 MiB per response, including icons; review if INMET expands its forecast horizon.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class InmetClient:
    """Fetch municipality forecasts with a finite per-socket timeout.

    No credentials, persistent session, automatic retries, or caching are used.
    ``timeout`` is a socket-operation limit, not a total request deadline.
    """

    def __init__(self, *, timeout: float = 20.0) -> None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("Timeout must be a positive, finite number of seconds.")
        self.timeout = timeout

    def get_forecast(self, code: str | int) -> dict[str, Any]:
        """GET /previsao/{IBGE_CODE} and return validated, unmodified JSON."""
        selected = municipality_code(code)
        request = Request(
            f"{FORECAST_BASE_URL}/previsao/{selected}",
            headers={"Accept": "application/json", "User-Agent": "inmet-forecast/0.1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise InmetHTTPError(response.status)
                content_type = response.headers.get_content_type()
                if content_type != "application/json" and not content_type.endswith("+json"):
                    raise InmetResponseError("INMET returned non-JSON content.")
                declared_length = response.length
                if declared_length is not None and declared_length > MAX_RESPONSE_BYTES:
                    raise InmetResponseError("INMET response exceeded the 8 MiB limit.")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if declared_length is not None and len(body) < declared_length:
                    raise InmetNetworkError(
                        "INMET connection ended before the response was complete."
                    )
        except HTTPError as error:
            status = error.code
            error.close()
            raise InmetHTTPError(status) from None
        except (URLError, TimeoutError, OSError, HTTPException):
            raise InmetNetworkError(
                "Could not reach INMET. Check connectivity and retry; "
                "increase timeout if the service is slow."
            ) from None
        if not body.strip():
            raise InmetResponseError("INMET returned an empty response.")
        if len(body) > MAX_RESPONSE_BYTES:
            raise InmetResponseError("INMET response exceeded the 8 MiB limit.")
        try:
            payload = json.loads(body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            raise InmetResponseError("INMET returned invalid UTF-8 JSON.") from None
        return validate_forecast(payload, selected)


def fetch_forecast(code: str | int, *, timeout: float = 20.0) -> dict[str, Any]:
    """Fetch raw forecast JSON using a temporary client."""
    return InmetClient(timeout=timeout).get_forecast(code)
