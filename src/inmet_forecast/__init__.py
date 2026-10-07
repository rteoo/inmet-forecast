"""Fetch and normalize official INMET municipality forecasts."""

from .client import InmetClient, fetch_forecast
from .errors import InmetError, InmetHTTPError, InmetNetworkError, InmetResponseError
from .forecast import normalize_forecast

__version__ = "0.1.0"
__all__ = [
    "InmetClient",
    "InmetError",
    "InmetHTTPError",
    "InmetNetworkError",
    "InmetResponseError",
    "fetch_forecast",
    "normalize_forecast",
]
