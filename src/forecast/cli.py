"""Command-line forecast output as UTF-8 JSON."""

import argparse
import json
import sys
from collections.abc import Sequence

from .client import fetch_forecast
from .errors import InmetError
from .forecast import normalize_forecast


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch an INMET municipality forecast as JSON.")
    parser.add_argument("municipality_code", help="Seven-digit IBGE code, e.g. 5218508")
    parser.add_argument("--timeout", type=float, default=20.0, help="Socket timeout in seconds")
    parser.add_argument(
        "--raw", action="store_true", help="Original JSON, including embedded icons"
    )
    parser.add_argument(
        "--include-icons", action="store_true", help="Keep icons in normalized rows"
    )
    args = parser.parse_args(argv)
    try:
        payload = fetch_forecast(args.municipality_code, timeout=args.timeout)
        output = (
            payload
            if args.raw
            else normalize_forecast(
                payload, args.municipality_code, include_icons=args.include_icons
            )
        )
    except (InmetError, ValueError) as error:
        print(f"inmet-forecast: {error}", file=sys.stderr)
        return 1
    # Emit UTF-8 on Windows too, including when stdout is redirected.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0
