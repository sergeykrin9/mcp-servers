import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("yadirect_server", Path(__file__).with_name("server.py"))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def response(status, text="", retry=None):
    return SimpleNamespace(status_code=status, text=text, headers={} if retry is None else {"retryIn": retry})


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def post(self, url, headers, json):
        self.requests.append((url, headers, json))
        return next(self.responses)


class ReportTests(unittest.TestCase):
    def run_report(self, responses):
        client = Client(responses)
        with patch.object(server, "_get_token", return_value="test-token"), \
             patch.object(server.httpx, "Client", return_value=client), \
             patch.object(server.time, "sleep") as sleep:
            result = server._request_report({"FieldNames": ["Date", "Cost"]})
        return result, client, sleep

    def test_queue_pending_ready_and_reuse_request(self):
        body = "Date\tCost\n2026-10-01\t123.45\n"
        result, client, sleep = self.run_report([
            response(201, "queued", "2"), response(202, "pending", "3"), response(200, body)
        ])
        self.assertEqual(result, body)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 3])
        self.assertEqual(client.requests[0], client.requests[1])
        self.assertEqual(client.requests[1], client.requests[2])
        self.assertEqual(client.requests[0][1]["returnMoneyInMicros"], "false")

    def test_ready_empty_report_has_valid_header(self):
        result, _, sleep = self.run_report([response(200, "Date\tCost\n")])
        self.assertEqual(server._parse_tsv(result), [])
        sleep.assert_not_called()

    def test_bad_success_body_is_not_silently_returned(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected TSV header"):
            self.run_report([response(200, "queued but incorrectly marked ready")])

    def test_error_is_not_misread_as_empty_data(self):
        with self.assertRaisesRegex(RuntimeError, "status 400"):
            self.run_report([response(400, "invalid report")])

    def test_timeout_is_bounded_and_does_not_sleep_after_final_attempt(self):
        client = Client([response(202, retry="0")] * 30)
        with patch.object(server, "_get_token", return_value="test-token"), \
             patch.object(server.httpx, "Client", return_value=client), \
             patch.object(server.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                server._request_report({"FieldNames": ["Date"]})
        self.assertEqual(len(client.requests), 30)
        self.assertEqual(sleep.call_count, 29)

    def test_invalid_retry_header_uses_default(self):
        _, _, sleep = self.run_report([response(201, retry="invalid"), response(200, "Date\tCost\n")])
        sleep.assert_called_once_with(5)

    def test_each_public_report_requests_currency_units_and_vat(self):
        def fake_request(definition, return_money_in_micros):
            self.assertFalse(return_money_in_micros)
            self.assertEqual(definition["IncludeVAT"], "YES")
            fields = definition["FieldNames"]
            values = ["123.45" if name == "Cost" else "1" for name in fields]
            return "\t".join(fields) + "\n" + "\t".join(values) + "\n"

        with patch.object(server, "_request_report", side_effect=fake_request):
            for tool in (server.get_campaign_stats, server.get_search_queries, server.get_daily_report):
                with self.subTest(tool=tool.__name__):
                    rows = json.loads(tool(42, 7))
                    self.assertEqual(rows[0]["Cost"], "123.45")


if __name__ == "__main__":
    unittest.main()
