import io
import json
import unittest
from contextlib import redirect_stderr
from unittest.mock import call, patch
from urllib.error import HTTPError, URLError

from chaintrace.rpc import rpc_call


def response(result):
    return io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}))


class RPCTimeoutRetryTests(unittest.TestCase):
    def test_two_timeouts_then_success_reuses_params_and_waits_twice(self):
        params = [{"fromBlock": "0x123", "toBlock": "0x124"}]
        with (
            patch("chaintrace.rpc.urlopen", side_effect=[
                TimeoutError(), URLError(TimeoutError()), response([]),
            ]) as transport,
            patch("chaintrace.rpc.sleep") as wait,
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(rpc_call("https://offline.invalid", "eth_getLogs", params), [])
        self.assertEqual(transport.call_count, 3)
        wait.assert_has_calls([call(1), call(2)])
        self.assertEqual(wait.call_count, 2)
        payloads = [json.loads(item.args[0].data) for item in transport.call_args_list]
        self.assertTrue(all(item == payloads[0] for item in payloads))
        self.assertEqual(payloads[0]["params"], params)

    def test_third_timeout_is_failure_not_empty_result(self):
        with (
            patch("chaintrace.rpc.urlopen", side_effect=TimeoutError()) as transport,
            patch("chaintrace.rpc.sleep") as wait,
            redirect_stderr(io.StringIO()),
        ):
            with self.assertRaisesRegex(ValueError, "已尝试 3 次"):
                rpc_call("https://offline.invalid", "eth_getLogs")
        self.assertEqual(transport.call_count, 3)
        self.assertEqual(wait.call_count, 2)

    def test_other_http_statuses_are_not_retried(self):
        for status in (403, 503):
            with (
                self.subTest(status=status),
                patch("chaintrace.rpc.urlopen", side_effect=HTTPError(
                    "https://offline.invalid", status, "error", None, None,
                )) as transport,
                patch("chaintrace.rpc.sleep") as wait,
            ):
                with self.assertRaisesRegex(ValueError, str(status)):
                    rpc_call("https://offline.invalid", "eth_getLogs")
                self.assertEqual(transport.call_count, 1)
                wait.assert_not_called()

    def test_non_timeout_connection_error_is_not_retried(self):
        with (
            patch("chaintrace.rpc.urlopen", side_effect=URLError(ConnectionRefusedError())) as transport,
            patch("chaintrace.rpc.sleep") as wait,
        ):
            with self.assertRaisesRegex(ValueError, "连接失败"):
                rpc_call("https://offline.invalid", "eth_getLogs")
        self.assertEqual(transport.call_count, 1)
        wait.assert_not_called()

    def test_invalid_json_or_rpc_error_is_not_retried(self):
        for body in ("not-json", '{"jsonrpc":"2.0","id":1,"error":{"code":-32602}}'):
            with (
                self.subTest(body=body),
                patch("chaintrace.rpc.urlopen", return_value=io.StringIO(body)) as transport,
                patch("chaintrace.rpc.sleep") as wait,
            ):
                with self.assertRaises(ValueError):
                    rpc_call("https://offline.invalid", "eth_getLogs")
                self.assertEqual(transport.call_count, 1)
                wait.assert_not_called()

    def test_write_method_does_not_inherit_read_retry_policy(self):
        with (
            patch("chaintrace.rpc.urlopen", side_effect=TimeoutError()) as transport,
            patch("chaintrace.rpc.sleep") as wait,
        ):
            with self.assertRaisesRegex(ValueError, "已尝试 1 次"):
                rpc_call("https://offline.invalid", "eth_sendRawTransaction", ["0x00"])
        self.assertEqual(transport.call_count, 1)
        wait.assert_not_called()
