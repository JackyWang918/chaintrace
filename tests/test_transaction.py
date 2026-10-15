import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.rpc import show_transaction


class TransactionOutcomeTests(unittest.TestCase):
    tx_hash = "0x" + "a" * 64
    block_hash = "0x" + "b" * 64

    def transaction(self, pending=False):
        return {
            "hash": self.tx_hash,
            "from": "0x" + "1" * 40,
            "to": "0x" + "2" * 40,
            "value": hex(10**18),
            "nonce": "0x0",
            "gas": hex(100000),
            "input": "0x",
            "blockNumber": None if pending else "0x123",
            "blockHash": None if pending else self.block_hash,
        }

    def receipt(self, status):
        return {
            "transactionHash": self.tx_hash,
            "blockNumber": "0x123",
            "blockHash": self.block_hash,
            "status": hex(status),
            "gasUsed": hex(21000),
            "effectiveGasPrice": hex(2 * 10**9),
        }

    def output(self, results):
        out = io.StringIO()
        with (
            patch("chaintrace.rpc.rpc_url", return_value="https://rpc.example"),
            patch("chaintrace.rpc.rpc_call", side_effect=results),
            redirect_stdout(out),
        ):
            show_transaction(self.tx_hash)
        return out.getvalue()

    def test_fee_uses_receipt_consumption_instead_of_request_limit(self):
        out = self.output(["0x1", self.transaction(), self.receipt(1)])
        self.assertIn("Execution: SUCCESS", out)
        self.assertIn("Gas limit (request): 100000", out)
        self.assertIn("42000000000000 wei = 0.000042 ETH", out)

    def test_failed_execution_still_reports_gas_fee(self):
        out = self.output(["0x1", self.transaction(), self.receipt(0)])
        self.assertIn("Execution: FAILED", out)
        self.assertIn("42000000000000 wei = 0.000042 ETH", out)

    def test_pending_receipt_is_not_reported_as_execution_failure(self):
        out = self.output(["0x1", self.transaction(pending=True), None])
        self.assertIn("pending", out)
        self.assertNotIn("Execution:", out)

    def test_unknown_transaction_is_not_reported_as_execution_failure(self):
        out = self.output(["0x1", None])
        self.assertIn("execution status unknown", out)
        self.assertNotIn("Execution:", out)
