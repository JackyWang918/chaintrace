import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.rpc import format_eth, format_units
from chaintrace.token import USDC_CONTRACT, read_uint256, show_token_balance


class TokenBalanceTests(unittest.TestCase):
    def test_decimal_precision_and_native_amount_compatibility(self):
        self.assertEqual(format_units(1234567, 6), "1.234567")
        self.assertEqual(format_units(1, 6), "0.000001")
        self.assertEqual(format_units(42, 0), "42")
        self.assertEqual(format_units(10**30 + 1, 6), "1000000000000000000000000.000001")
        self.assertEqual(format_eth(1), "0.000000000000000001")

    def test_empty_contract_response_is_not_a_zero_balance(self):
        with patch("chaintrace.token.rpc_call", return_value="0x"):
            with self.assertRaisesRegex(ValueError, "32"):
                read_uint256("https://rpc.example", "0x313ce567", "0x123")

    def test_both_calls_use_same_block_and_balance_call_encodes_holder(self):
        holder = "0x" + "1" * 40
        out = io.StringIO()
        with (
            patch("chaintrace.token.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.token.checked_mainnet"),
            patch("chaintrace.token.read_quantity", return_value=("0x123", 291)),
            patch("chaintrace.token.rpc_call", side_effect=[
                "0x" + format(6, "064x"), "0x" + format(1234567, "064x"),
            ]) as call,
            redirect_stdout(out),
        ):
            show_token_balance(holder)
        self.assertEqual(call.call_args_list[0].args[2], [
            {"to": USDC_CONTRACT, "data": "0x313ce567"}, "0x123",
        ])
        self.assertEqual(call.call_args_list[1].args[2], [
            {"to": USDC_CONTRACT, "data": "0x70a08231" + "0" * 24 + "1" * 40}, "0x123",
        ])
        self.assertIn("Token balance: 1.234567 USDC", out.getvalue())
