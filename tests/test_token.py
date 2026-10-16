import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.rpc import format_eth, format_units
from chaintrace.token import USDC_CONTRACT, read_abi_string, read_uint256, show_token_allowance, show_token_balance, show_token_info


class TokenBalanceTests(unittest.TestCase):
    def test_allowance_uses_owner_then_spender_at_same_block(self):
        owner = "0x" + "1" * 40
        spender = "0x" + "2" * 40
        out = io.StringIO()
        with (
            patch("chaintrace.token.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.token.checked_mainnet"),
            patch("chaintrace.token.read_quantity", return_value=("0x123", 291)),
            patch("chaintrace.token.rpc_call", side_effect=[
                "0x" + format(6, "064x"), "0x" + format(3000000, "064x"),
            ]) as call,
            redirect_stdout(out),
        ):
            show_token_allowance(owner, spender)
        self.assertEqual(call.call_args_list[1].args[2], [
            {"to": USDC_CONTRACT, "data": "0xdd62ed3e" + "0" * 24 + "1" * 40 + "0" * 24 + "2" * 40},
            "0x123",
        ])
        self.assertTrue(all(item.args[2][1] == "0x123" for item in call.call_args_list))
        self.assertIn("Remaining allowance: 3 USDC", out.getvalue())

    def test_token_info_reads_metadata_at_one_block(self):
        def abi_string(value: str) -> str:
            encoded = value.encode("utf-8")
            padded = encoded + bytes((-len(encoded)) % 32)
            return "0x" + (32).to_bytes(32).hex() + len(encoded).to_bytes(32).hex() + padded.hex()

        out = io.StringIO()
        with (
            patch("chaintrace.token.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.token.checked_mainnet"),
            patch("chaintrace.token.read_quantity", return_value=("0x123", 291)),
            patch("chaintrace.token.rpc_call", side_effect=[
                abi_string("USD Coin"), abi_string("USDC"), "0x" + format(6, "064x"),
            ]) as call,
            redirect_stdout(out),
        ):
            show_token_info()
        self.assertEqual([item.args[2][0]["data"] for item in call.call_args_list], [
            "0x06fdde03", "0x95d89b41", "0x313ce567",
        ])
        self.assertTrue(all(item.args[2][1] == "0x123" for item in call.call_args_list))
        self.assertIn("Name (contract): USD Coin", out.getvalue())
        self.assertIn("Decimals (contract): 6", out.getvalue())

    def test_empty_metadata_response_is_rejected(self):
        with patch("chaintrace.token.rpc_call", return_value="0x"):
            with self.assertRaisesRegex(ValueError, "ABI 字符串"):
                read_abi_string("https://rpc.example", "0x06fdde03", "0x123")

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
