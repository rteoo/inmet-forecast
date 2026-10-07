# inmetpy

A pip-installable Python client for INMET's Brazilian municipality forecasts.
Python 3.10+; no third-party runtime dependencies.

## Install locally

```powershell
python -m pip install C:\Users\rodri\Projects\inmetpy
```

This repository is local. It has not been published to PyPI; `pip install inmetpy`
is not the installation command for this checkout.

## Python

```python
from inmetpy import InmetClient, fetch_forecast, normalize_forecast

# Quirinópolis, Goiás (IBGE municipality code).
raw = fetch_forecast(5218508, timeout=20)
records = normalize_forecast(raw)

for record in records:
    print(record["date"], record["period"], record["resumo"])

# Reuse a configured client across requests.
client = InmetClient(timeout=30)
raw = client.get_forecast("5218508")
```

`fetch_forecast()` and `get_forecast()` return the original validated dictionary,
including base64 icons. `normalize_forecast()` returns chronological rows with
`municipality_code`, ISO `date`, and `period` (`morning`, `afternoon`, `night`, or
`daily`). Original INMET fields and Portuguese descriptions are retained. Embedded
images are excluded from normalized rows unless `include_icons=True`.

The first two dates currently contain `manha`, `tarde`, and `noite` objects; later
dates contain one daily object. Normalization detects the shape of each date
instead of assuming a fixed five-day horizon. Temperatures are Celsius and
humidity values are percentages; numeric values may be `None` when missing.
Dates arrive from INMET as `DD/MM/YYYY`.

## Command line

```powershell
inmetpy 5218508
python -m inmetpy 5218508 --timeout 30
python -m inmetpy 5218508 --raw
```

Default output is normalized UTF-8 JSON. `--raw` includes all original fields
and embedded images; `--include-icons` keeps images in normalized output.
Failures print an error to stderr and return exit status 1.

## Errors and service limits

Catch `InmetError` for service failures, or its specific subclasses:
`InmetHTTPError` (with `.status`), `InmetNetworkError`, and `InmetResponseError`.
Invalid codes and timeouts raise `ValueError` before making a request.
Responses are limited to 8 MiB, and must be nonempty UTF-8 JSON with valid forecast
entries. The timeout bounds individual socket operations, not total elapsed time.
There are no automatic retries or caches. Caller applications should cache
appropriately and label retrieval times.

Only forecasts are supported. They are not current station measurements.
The API has no moon-phase field in the response inspected on 2026-10-07.
Do not keep today's temperature header when showing tomorrow's forecast: use
the fields from the selected date/period.

## Source and verification

- [Forecast API example](https://apiprevmet3.inmet.gov.br/previsao/5218508)
- [Official forecast page](https://previsao.inmet.gov.br/5218508)
- [IBGE municipality](https://www.ibge.gov.br/cidades-e-estados/go/quirinopolis.html)
- [INMET forecast service](https://portal.inmet.gov.br/servicos/previs%C3%A3o-do-tempo)
- [API access contact](https://portal.inmet.gov.br/fale-conosco): api@inmet.gov.br

The official forecast frontend uses this API. An unauthenticated request returned
HTTP 200 on 2026-10-07; this is a point-in-time observation, not an authentication,
rate-limit, uptime, or schema guarantee. This project is an independent client
and is not affiliated with INMET. Data remains attributed to INMET; the MIT
license covers this client code, not a grant of rights over third-party data.

## Development

Tests use the standard library and a local HTTP server; they never call INMET.

```powershell
$env:PYTHONPATH = 'src'
python -W error::ResourceWarning -m unittest discover -s tests -v
python -m ruff check src tests
python -m build --no-isolation
python -m twine check dist/*
```

The build and lint commands use tooling already installed on the host. Tests
shut down their server and close their files even on failure.

Verified on Windows/Python 3.14.6 on 2026-10-07: 18 tests passed from source and
from an installed wheel, Ruff passed, wheel/sdist builds and Twine checks passed.
The installed CLI fetched nine forecast rows for Quirinópolis. October 7's
afternoon forecast matched 19–36°C, 30–90% humidity, light NE-E winds, and the
portal's showers/thunderstorms description. Other Python versions and operating
systems have not been exercised locally.
