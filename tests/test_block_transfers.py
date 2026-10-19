import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.token import USDC_CONTRACT
from chaintrace.transfer import TRANSFER_TOPIC, show_block_transfers


class BlockTransferTests(unittest.TestCase):
    block_hash = "0x" + "b" * 64
    tx_hash = "0x" + "a" * 64

    def block(self):
        return {"number": "0x123", "hash": self.block_hash, "timestamp": "0x456"}

    def log(self, index, amount):
        return {
            "address": USDC_CONTRACT, "blockHash": self.block_hash,
            "blockNumber": "0x123", "transactionHash": self.tx_hash,
            "logIndex": hex(index), "removed": False,
            "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + "1" * 40,
                       "0x" + "0" * 24 + "3" * 40],
            "data": "0x" + format(amount, "064x"),
        }

    def run_query(self, result):
        output = io.StringIO()
        with (
            patch("chaintrace.transfer.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.transfer.checked_mainnet"),
            patch("chaintrace.transfer.rpc_call", side_effect=[self.block(), result]) as call,
            patch("chaintrace.transfer.read_uint256") as metadata,
            redirect_stdout(output),
        ):
            show_block_transfers(291)
        metadata.assert_not_called()
        return output.getvalue(), call

    def test_same_transaction_keeps_multiple_logs_and_zero_amount_in_order(self):
        output, call = self.run_query([self.log(4, 2000000), self.log(0, 0)])
        self.assertIn("USDC Transfer logs: 2", output)
        self.assertIn("Distinct transactions with matching logs: 1", output)
        self.assertIn("Raw amount: 0 (token base units, not wei)", output)
        self.assertLess(output.index("Log index: 0"), output.index("Log index: 4"))
        self.assertEqual(call.call_args_list[1].args[1:], ("eth_getLogs", [{
            "fromBlock": "0x123", "toBlock": "0x123",
            "address": USDC_CONTRACT, "topics": [TRANSFER_TOPIC],
        }]))

    def test_empty_list_is_valid_but_null_or_rpc_error_is_not_empty(self):
        output, _ = self.run_query([])
        self.assertIn("USDC Transfer logs: 0", output)
        self.assertNotIn("  Raw amount:", output)
        for result in [None, ValueError("RPC HTTP 错误：403")]:
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.run_query(result)

    def test_wrong_block_removed_or_other_contract_is_rejected(self):
        for change in [
            {"blockHash": "0x" + "c" * 64}, {"blockNumber": "0x124"},
            {"removed": True}, {"address": "0x" + "4" * 40},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_query([dict(self.log(0, 1), **change)])

    def test_repeated_log_index_is_rejected_rather_than_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "重复 logIndex"):
            self.run_query([self.log(4, 1), self.log(4, 2)])
