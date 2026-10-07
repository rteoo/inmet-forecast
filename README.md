# inmet-forecast

<p align="center">
  <img src="docs/inmet-forecast-icon.png" width="128" alt="inmet-forecast weather icon: sun, cloud, and rain">
</p>

<p align="center">
  A dependency-free Python client for INMET's Brazilian municipality forecasts,
  with raw API data, normalized records, and a JSON command line.
</p>

<p align="center">
  <a href="https://github.com/rteoo/inmet-forecast/actions/workflows/publish.yml"><img src="https://github.com/rteoo/inmet-forecast/actions/workflows/publish.yml/badge.svg" alt="Publishing workflow status"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10 or later">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license"></a>
</p>

Fetch forecasts by IBGE municipality code from Python or the command line.
Keep INMET's original JSON or turn its period-based and daily entries into
chronological records without losing Portuguese descriptions or unknown fields.

## Highlights

- Municipality forecasts from INMET's forecast API, including temperature,
  humidity, wind, weather descriptions, sunrise, and sunset when supplied.
- Raw responses and normalized morning, afternoon, night, and daily records.
- UTF-8 JSON output through `inmet-forecast` or `python -m forecast`.
- Configurable socket timeouts, bounded responses, and specific error classes.
- Python 3.10 or later, using only the standard library at runtime.

## Quick start

Install from a repository checkout:

```powershell
git clone https://github.com/rteoo/inmet-forecast.git
cd inmet-forecast
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
python -m forecast 5218508
```

Use `python -m pip install -e .` for an editable development install. The
distribution and console command are named `inmet-forecast`; the Python import
is `forecast`. The example uses Quirinópolis, Goiás, municipality code `5218508`.

## Python

```python
from forecast import InmetClient, fetch_forecast, normalize_forecast

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
inmet-forecast 5218508
python -m forecast 5218508 --timeout 30
python -m forecast 5218508 --raw
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

## Publishing to PyPI

`.github/workflows/publish.yml` publishes when a GitHub release is published. It tests
the installed package on Python 3.10 through 3.14, checks lint and formatting,
builds and validates a wheel and source distribution, then uploads those same
artifacts using [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/).
No PyPI API token is needed. A manual workflow run performs validation only.

Before the first release:

1. Create the GitHub repository environment `pypi`. Configure required reviewers
   and restrict its deployment tags to `v*` where the repository plan permits.
2. Register a [pending PyPI publisher](https://pypi.org/manage/account/publishing/)
   with project name `inmet-forecast`, owner `rteoo`, repository `inmet-forecast`,
   workflow filename `publish.yml`, and environment `pypi`.
3. Publish a GitHub release whose tag exactly matches `v` plus the version in
   `pyproject.toml`, initially `v0.1.0`. The tagged commit must contain the workflow.

For later releases, update the package version before tagging. PyPI versions
cannot be overwritten. The workflow deliberately fails on an existing version
instead of silently skipping its upload. GitHub Actions execution and PyPI
publication have not been verified from this local checkout.

## License

This client is released under the [MIT License](LICENSE). Weather data remains
attributed to INMET. The [project icon](docs/inmet-forecast-icon.png) is an
independent weather mark; its design reference and generation prompt are recorded
in [docs/README.md](docs/README.md).
