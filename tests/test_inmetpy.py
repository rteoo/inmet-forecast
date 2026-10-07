import copy
import io
import json
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from inmetpy import (
    InmetClient,
    InmetHTTPError,
    InmetNetworkError,
    InmetResponseError,
    fetch_forecast,
    normalize_forecast,
)
from inmetpy.cli import main

CODE = "5218508"


def entry(**updates):
    data = {
        "uf": "GO",
        "entidade": "Quirinópolis",
        "resumo": "Muitas nuvens com chuva isolada",
        "temp_min": 19,
        "temp_max": 36,
        "umidade_min": 30,
        "umidade_max": 90,
        "dir_vento": "SE-S",
        "int_vento": "Fracos",
        "icone": "data:image/png;base64,fixture",
    }
    return dict(data, **updates)


def forecast():
    # Date ordering intentionally crosses months and differs from insertion order.
    return {
        CODE: {
            "01/11/2026": entry(temp_min=23, temp_max=39),
            "31/10/2026": {
                "noite": entry(),
                "manha": entry(resumo="Poucas nuvens", temp_min=21, temp_max=39),
                "tarde": entry(resumo="Muitas nuvens com pancadas de chuva e trovoadas"),
            },
        }
    }


@contextmanager
def serve(body, *, status=200, content_type="application/json", delay=0, truncated=False):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, self.headers.get("Accept")))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body) + (100 if truncated else 0)))
            self.end_headers()
            if delay:
                time.sleep(delay)
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # The timeout test deliberately closes the client's socket.

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        with patch("inmetpy.client.FORECAST_BASE_URL", f"http://127.0.0.1:{server.server_port}"):
            yield requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("Test HTTP server did not stop.")


class ClientTests(unittest.TestCase):
    def test_real_http_get_preserves_unicode_payload_and_headers(self):
        payload = forecast()
        with serve(json.dumps(payload, ensure_ascii=False).encode("utf-8")) as requests:
            self.assertEqual(fetch_forecast(5218508), payload)
        self.assertEqual(requests, [("GET", "/previsao/5218508", "application/json")])

    def test_http_errors_expose_status_without_response_body(self):
        for status in (403, 404, 429, 500):
            with self.subTest(status=status), serve(b"private upstream detail", status=status):
                with self.assertRaises(InmetHTTPError) as caught:
                    fetch_forecast(CODE)
                self.assertEqual(caught.exception.status, status)
                self.assertNotIn("private", str(caught.exception))

    def test_non_json_empty_malformed_and_wrong_city_responses(self):
        scenarios = [
            (b"<html>upstream error</html>", "text/html"),
            (b"", "application/json"),
            (b"not json", "application/json"),
            (b"\xff", "application/json"),
            (b"[]", "application/json"),
            (b'{"5218508":{}}', "application/json"),
            (b'{"5300108":{}}', "application/json"),
        ]
        for body, content_type in scenarios:
            with self.subTest(body=body), serve(body, content_type=content_type):
                with self.assertRaises(InmetResponseError):
                    fetch_forecast(CODE)

    def test_utf8_bom_and_json_suffix_content_type(self):
        body = b"\xef\xbb\xbf" + json.dumps(forecast()).encode()
        with serve(body, content_type="application/vnd.inmet+json"):
            self.assertEqual(fetch_forecast(CODE), forecast())

    def test_no_content_is_not_a_successful_forecast(self):
        with serve(b"", status=204):
            with self.assertRaises(InmetHTTPError) as caught:
                fetch_forecast(CODE)
            self.assertEqual(caught.exception.status, 204)

    def test_read_timeout_becomes_network_error_and_does_not_retry(self):
        with serve(json.dumps(forecast()).encode(), delay=0.1) as requests:
            with self.assertRaises(InmetNetworkError):
                fetch_forecast(CODE, timeout=0.02)
        self.assertEqual(len(requests), 1)

    def test_truncated_http_body_becomes_network_error(self):
        with serve(b"{", truncated=True):
            with self.assertRaises(InmetNetworkError):
                fetch_forecast(CODE)

    def test_response_size_limit(self):
        with patch("inmetpy.client.MAX_RESPONSE_BYTES", 8), serve(b"123456789"):
            with self.assertRaisesRegex(InmetResponseError, "limit"):
                fetch_forecast(CODE)

    def test_invalid_inputs_make_no_request(self):
        with patch("inmetpy.client.urlopen") as opener:
            for code in (True, None, 1.0, "5218508/x", "１２３４５６７", "", "123456"):
                with self.subTest(code=code), self.assertRaises(ValueError):
                    fetch_forecast(code)
            for timeout in (True, None, 0, -1, "20", float("nan"), float("inf")):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    InmetClient(timeout=timeout)
            opener.assert_not_called()


class NormalizationTests(unittest.TestCase):
    def test_mixed_shapes_sort_by_calendar_date_and_preserve_period_data(self):
        rows = normalize_forecast(forecast())
        self.assertEqual(
            [(row["date"], row["period"]) for row in rows],
            [
                ("2026-10-31", "morning"),
                ("2026-10-31", "afternoon"),
                ("2026-10-31", "night"),
                ("2026-11-01", "daily"),
            ],
        )
        self.assertEqual(rows[0]["temp_min"], 21)
        self.assertEqual(rows[0]["resumo"], "Poucas nuvens")
        self.assertEqual(rows[2]["dir_vento"], "SE-S")
        self.assertEqual(rows[3]["municipality_code"], CODE)

    def test_icons_are_optional_and_raw_payload_is_not_mutated(self):
        payload = forecast()
        before = copy.deepcopy(payload)
        self.assertNotIn("icone", normalize_forecast(payload)[0])
        self.assertIn("icone", normalize_forecast(payload, include_icons=True)[0])
        self.assertEqual(payload, before)

    def test_null_numeric_values_are_preserved(self):
        rows = normalize_forecast({CODE: {"07/10/2026": entry(temp_min=None)}})
        self.assertIsNone(rows[0]["temp_min"])

    def test_unknown_fields_are_retained(self):
        rows = normalize_forecast({CODE: {"07/10/2026": entry(new_field="future")}})
        self.assertEqual(rows[0]["new_field"], "future")

    def test_partial_period_day_is_supported(self):
        rows = normalize_forecast({CODE: {"07/10/2026": {"noite": entry()}}})
        self.assertEqual(rows[0]["period"], "night")

    def test_malformed_dates_and_entries_are_rejected(self):
        for day, value in [
            ("31/02/2026", entry()),
            ("7/10/2026", entry()),
            ("07/10/2026", {}),
            ("07/10/2026", {"manha": entry(), "other": {}}),
            ("07/10/2026", entry(resumo="")),
            ("07/10/2026", entry(temp_min="19")),
            ("07/10/2026", entry(temp_max=float("nan"))),
            ("07/10/2026", entry(umidade_min=True)),
        ]:
            with self.subTest(day=day, value=value), self.assertRaises(InmetResponseError):
                normalize_forecast({CODE: {day: value}})

    def test_multiple_cities_require_explicit_selection(self):
        payload = dict(forecast(), **{"5300108": {"07/10/2026": entry(entidade="Brasília")}})
        with self.assertRaises(ValueError):
            normalize_forecast(payload)
        self.assertEqual(normalize_forecast(payload, CODE)[0]["entidade"], "Quirinópolis")


class CLITests(unittest.TestCase):
    def test_normalized_and_raw_cli_json(self):
        with patch("inmetpy.cli.fetch_forecast", return_value=forecast()):
            for extra, expected in [([], normalize_forecast(forecast())), (["--raw"], forecast())]:
                with self.subTest(extra=extra), redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main([CODE, *extra]), 0)
                    self.assertEqual(json.loads(output.getvalue()), expected)

    def test_cli_failure_returns_nonzero_without_traceback(self):
        with patch("inmetpy.cli.fetch_forecast", side_effect=InmetHTTPError(429)):
            with redirect_stderr(io.StringIO()) as error, redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([CODE]), 1)
                self.assertIn("HTTP 429", error.getvalue())
                self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
