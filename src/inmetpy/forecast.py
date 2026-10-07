"""Validate INMET's date-keyed JSON and flatten its two forecast shapes."""

import math
from datetime import datetime
from typing import Any

from .errors import InmetResponseError

PERIODS = {"manha": "morning", "tarde": "afternoon", "noite": "night"}


def municipality_code(value: str | int) -> str:
    """Return a seven-digit IBGE code, without accepting URL fragments."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Municipality code must be a seven-digit IBGE code.")
    code = str(value)
    if len(code) != 7 or not code.isascii() or not code.isdigit():
        raise ValueError("Municipality code must be a seven-digit IBGE code.")
    return code


def _date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y")
    except (ValueError, TypeError):
        raise InmetResponseError("INMET returned an invalid forecast date.") from None
    if parsed.strftime("%d/%m/%Y") != value:
        raise InmetResponseError("INMET returned an invalid forecast date.")
    return parsed.date().isoformat()


def _entry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InmetResponseError("INMET returned an invalid forecast entry.")
    for key in ("uf", "entidade", "resumo"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise InmetResponseError(f"INMET forecast is missing a valid {key} field.")
    for key in ("temp_min", "temp_max", "umidade_min", "umidade_max"):
        if key not in value:
            raise InmetResponseError(f"INMET forecast is missing {key}.")
        number = value[key]
        if number is not None and (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(number)
        ):
            raise InmetResponseError(f"INMET forecast has an invalid {key} value.")
    return value


def validate_forecast(payload: Any, code: str) -> dict[str, Any]:
    """Validate the requested municipality while retaining all original fields."""
    if not isinstance(payload, dict) or not isinstance(payload.get(code), dict):
        raise InmetResponseError("INMET response does not contain the requested municipality.")
    days = payload[code]
    if not days:
        raise InmetResponseError("INMET returned no forecasts for the requested municipality.")
    for day, value in days.items():
        _date(day)
        if not isinstance(value, dict) or not value:
            raise InmetResponseError("INMET returned an invalid forecast day.")
        period_keys = set(value).intersection(PERIODS)
        if period_keys:
            if set(value) != period_keys:
                raise InmetResponseError("INMET returned a mixed or unknown forecast period.")
            for period in period_keys:
                _entry(value[period])
        else:
            _entry(value)
    return payload


def normalize_forecast(
    payload: dict[str, Any],
    code: str | int | None = None,
    *,
    include_icons: bool = False,
) -> list[dict[str, Any]]:
    """Return chronological rows with ISO dates and English period identifiers.

    Original INMET field names and Portuguese descriptions are preserved. Embedded
    images are omitted by default. The input payload is never modified.
    """
    if code is None:
        if not isinstance(payload, dict) or len(payload) != 1:
            raise ValueError(
                "Supply a municipality code for a response with multiple municipalities."
            )
        code = next(iter(payload))
    selected = municipality_code(code)
    days = validate_forecast(payload, selected)[selected]
    records = []
    for day in sorted(days, key=_date):
        value = days[day]
        entries = (
            [(PERIODS[period], value[period]) for period in PERIODS if period in value]
            if set(value).intersection(PERIODS)
            else [("daily", value)]
        )
        for period, entry in entries:
            record = {
                key: item
                for key, item in entry.items()
                if include_icons or not (isinstance(item, str) and item.startswith("data:image/"))
            }
            record.update(municipality_code=selected, date=_date(day), period=period)
            records.append(record)
    return records
