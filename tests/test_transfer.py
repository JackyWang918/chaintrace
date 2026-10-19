import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.transfer import TRANSFER_TOPIC, decode_transfer, show_transfers
from chaintrace.token import USDC_CONTRACT


class TransferTests(unittest.TestCase):
    def log(self, amount=2000000):
        return {
            "address": USDC_CONTRACT,
            "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + "1" * 40,
                       "0x" + "0" * 24 + "3" * 40],
            "data": "0x" + format(amount, "064x"),
        }

    def test_decodes_addresses_and_integer_including_zero(self):
        self.assertEqual(decode_transfer(self.log()),
                         ("0x" + "1" * 40, "0x" + "3" * 40, 2000000))
        self.assertEqual(decode_transfer(self.log(0))[2], 0)

    def test_same_event_from_other_contract_is_not_usdc(self):
        log = self.log()
        log["address"] = "0x" + "4" * 40
        self.assertIsNone(decode_transfer(log))
        log = self.log()
        log["topics"][0] = "0x" + "5" * 64
        self.assertIsNone(decode_transfer(log))

    def test_empty_amount_and_bad_address_padding_are_rejected(self):
        log = self.log()
        log["data"] = "0x"
        with self.assertRaisesRegex(ValueError, "32"):
            decode_transfer(log)
        log = self.log()
        log["topics"][1] = "0x" + "f" * 64
        with self.assertRaisesRegex(ValueError, "ABI address"):
            decode_transfer(log)

    def test_missing_receipt_is_unknown_not_zero_transfers(self):
        tx_hash = "0x" + "a" * 64
        out = io.StringIO()
        with (
            patch("chaintrace.transfer.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.transfer.checked_mainnet"),
            patch("chaintrace.transfer.rpc_call", side_effect=[
                {"hash": tx_hash, "from": "B", "to": USDC_CONTRACT}, None,
            ]),
            redirect_stdout(out),
        ):
            show_transfers(tx_hash)
        self.assertIn("execution status unknown", out.getvalue())
        self.assertNotIn("USDC Transfer logs: 0", out.getvalue())

    def test_transaction_caller_is_not_used_as_token_sender(self):
        tx_hash = "0x" + "a" * 64
        block_hash = "0x" + "b" * 64
        context = {"transactionHash": tx_hash, "blockHash": block_hash, "blockNumber": "0x123"}
        log = dict(self.log(), **context, removed=False, logIndex="0x7")
        receipt = dict(context, status="0x1", logs=[log])
        out = io.StringIO()
        with (
            patch("chaintrace.transfer.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.transfer.checked_mainnet"),
            patch("chaintrace.transfer.read_uint256", return_value=6) as decimals,
            patch("chaintrace.transfer.rpc_call", side_effect=[
                {"hash": tx_hash, "from": "B", "to": USDC_CONTRACT,
                 "blockHash": block_hash, "blockNumber": "0x123"}, receipt,
            ]),
            redirect_stdout(out),
        ):
            show_transfers(tx_hash)
        self.assertIn("Transaction from (caller): B", out.getvalue())
        self.assertIn("Token from: 0x" + "1" * 40, out.getvalue())
        self.assertIn("Amount: 2 USDC", out.getvalue())
        self.assertEqual(decimals.call_args.args[2], "0x123")
