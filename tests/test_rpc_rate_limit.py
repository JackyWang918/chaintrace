import io
import json
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from unittest.mock import call, patch
from urllib.error import HTTPError

from chaintrace.rpc import rpc_call


def limited(value=None):
    headers = {} if value is None else {"Retry-After": value}
    return HTTPError("https://offline.invalid", 429, "Too Many Requests", headers, None)


def success():
    return io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": []}))


class RPCRateLimitTests(unittest.TestCase):
    def invoke(self, responses, method="eth_getLogs"):
        with (
            patch("chaintrace.rpc.urlopen", side_effect=responses) as transport,
            patch("chaintrace.rpc.sleep") as wait,
            patch("chaintrace.rpc.datetime") as clock,
            redirect_stderr(io.StringIO()),
        ):
            clock.now.return_value = datetime(2026, 10, 22, 0, 0, 0, 500000, tzinfo=timezone.utc)
            try:
                result = rpc_call("https://offline.invalid", method, [{"fromBlock": "0x123", "toBlock": "0x124"}])
            except ValueError as exc:
                result = exc
        return result, transport, wait

    def test_seconds_header_is_respected_and_empty_success_returns(self):
        result, transport, wait = self.invoke([limited("5"), success()])
        self.assertEqual(result, [])
        self.assertEqual(transport.call_count, 2)
        wait.assert_called_once_with(5)
        payloads = [json.loads(item.args[0].data) for item in transport.call_args_list]
        self.assertEqual(payloads[0], payloads[1])

    def test_http_date_formats_are_utc_and_delay_rounds_up(self):
        for value in ["Thu, 22 Oct 2026 00:00:05 GMT", "Thursday, 22-Oct-26 00:00:05 GMT",
                      "Thu Oct 22 00:00:05 2026"]:
            with self.subTest(value=value):
                result, _, wait = self.invoke([limited(value), success()])
                self.assertEqual(result, [])
                wait.assert_called_once_with(5)

    def test_missing_header_uses_backoff_and_exhausts_at_three(self):
        result, transport, wait = self.invoke([limited(), limited(), limited(), success()])
        self.assertIsInstance(result, ValueError)
        self.assertIn("429", str(result))
        self.assertIn("已尝试 3 次", str(result))
        self.assertEqual(transport.call_count, 3)
        self.assertEqual(wait.call_args_list, [call(1), call(2)])

    def test_malformed_header_stops_without_waiting_or_guessing(self):
        for value in ("", "soon", "-1", "1.5"):
            with self.subTest(value=value):
                result, transport, wait = self.invoke([limited(value), success()])
                self.assertIsInstance(result, ValueError)
                self.assertIn("格式无效", str(result))
                self.assertEqual(transport.call_count, 1)
                wait.assert_not_called()

    def test_wait_limit_stops_instead_of_shortening_server_delay(self):
        result, transport, wait = self.invoke([limited("31"), success()])
        self.assertIsInstance(result, ValueError)
        self.assertIn("30 秒上限", str(result))
        self.assertEqual(transport.call_count, 1)
        wait.assert_not_called()
        result, _, wait = self.invoke([limited("30"), success()])
        self.assertEqual(result, [])
        wait.assert_called_once_with(30)

    def test_timeout_and_rate_limit_share_budget_without_reset(self):
        result, transport, wait = self.invoke([TimeoutError(), limited("5"), TimeoutError(), success()])
        self.assertIsInstance(result, ValueError)
        self.assertIn("已尝试 3 次", str(result))
        self.assertEqual(transport.call_count, 3)
        self.assertEqual(wait.call_args_list, [call(1), call(5)])

    def test_zero_past_or_short_delay_does_not_create_a_tight_loop(self):
        for value in ("0", "Thu, 01 Jan 1970 00:00:00 GMT"):
            with self.subTest(value=value):
                result, _, wait = self.invoke([limited(value), success()])
                self.assertEqual(result, [])
                wait.assert_called_once_with(1)
        result, _, wait = self.invoke([limited("0"), limited("1"), success()])
        self.assertEqual(result, [])
        self.assertEqual(wait.call_args_list, [call(1), call(2)])

    def test_write_method_does_not_retry_on_429(self):
        result, transport, wait = self.invoke([limited("5"), success()], "eth_sendRawTransaction")
        self.assertIsInstance(result, ValueError)
        self.assertIn("已尝试 1 次", str(result))
        self.assertEqual(transport.call_count, 1)
        wait.assert_not_called()
