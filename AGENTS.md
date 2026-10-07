# inmet-forecast

Independent Python client for INMET municipality forecasts. Source lives in
`src/inmet_forecast`; tests live in `tests`. The runtime uses only the standard library.

The API's first two dates currently contain named forecast periods, while later
dates contain daily objects. Detect shape per date; retain Portuguese text and
unknown entry fields. Current station observations are outside this package's
implemented scope. Treat endpoint availability and schema as external state.

Verified commands on Windows with Python 3.14.6:

```powershell
$env:PYTHONPATH = 'src'
python -W error::ResourceWarning -m unittest discover -s tests -v
python -m ruff check src tests
python -m ruff format --check src tests
python -m build --no-isolation
python -m twine check dist/*
```

Tests use local HTTP fixtures and close all resources. Live verification is
separate: `python -m inmet_forecast 5218508 --timeout 30`. Do not add live calls to the
ordinary test suite. After packaging changes, install the wheel in a disposable
environment and exercise the installed import and CLI; clean up that environment.

Use task branches and focused local commits. Generated build outputs and caches
are ignored. This repository has no configured remote or publication workflow.
