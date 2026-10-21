import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from chaintrace import main
from chaintrace.storage import collect_transfers, save_transfers
from chaintrace.token import USDC_CONTRACT
from chaintrace.transfer import TransferRecord


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "logs.sqlite3"
        self.record = TransferRecord(
            chain_id=1, token_contract=USDC_CONTRACT.lower(), block_number=291,
            block_hash="0x" + "b" * 64, transaction_hash="0x" + "a" * 64,
            log_index=0, sender="0x" + "1" * 40, recipient="0x" + "3" * 40,
            raw_amount=1234567, block_timestamp=1000,
        )

    def count(self):
        with sqlite3.connect(self.path) as connection:
            return connection.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]

    def test_repeat_is_idempotent_and_zero_and_uint256_are_exact_text(self):
        records = [replace(self.record, raw_amount=0),
                   replace(self.record, log_index=1, raw_amount=2**256 - 1)]
        self.assertEqual(save_transfers(self.path, records), (2, 0, 2))
        self.assertEqual(save_transfers(self.path, records), (0, 2, 2))
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT raw_amount, typeof(raw_amount) FROM transfers ORDER BY log_index"
            ).fetchall()
        self.assertEqual(rows, [("0", "text"), (str(2**256 - 1), "text")])
        self.assertEqual(save_transfers(self.path, []), (0, 0, 2))

    def test_same_identity_conflict_rolls_back_new_rows_in_the_batch(self):
        save_transfers(self.path, [self.record])
        for change in [{"raw_amount": 7}, {"block_number": 292},
                       {"transaction_hash": "0x" + "c" * 64}]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "内容冲突"):
                save_transfers(self.path, [replace(self.record, log_index=1),
                                           replace(self.record, **change)])
            self.assertEqual(self.count(), 1)

    def test_different_chain_or_block_hash_is_a_distinct_observation(self):
        records = [self.record, replace(self.record, chain_id=2),
                   replace(self.record, block_hash="0x" + "c" * 64)]
        self.assertEqual(save_transfers(self.path, records), (3, 0, 3))

    def test_sql_error_rolls_back_the_whole_batch(self):
        save_transfers(self.path, [self.record])
        with sqlite3.connect(self.path) as connection:
            connection.execute("""
                CREATE TRIGGER reject_test_row BEFORE INSERT ON transfers
                WHEN NEW.log_index = 2
                BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END
            """)
        with self.assertRaisesRegex(ValueError, "SQLite 写入失败"):
            save_transfers(self.path, [replace(self.record, log_index=1),
                                       replace(self.record, log_index=2)])
        self.assertEqual(self.count(), 1)

    def test_rpc_failure_does_not_create_database(self):
        with patch("chaintrace.storage.read_block_transfers", side_effect=ValueError("HTTP 403")):
            with self.assertRaisesRegex(ValueError, "HTTP 403"):
                collect_transfers(291, 292, self.path)
        self.assertFalse(self.path.exists())

    def test_float_negative_or_overflow_amount_is_rejected(self):
        save_transfers(self.path, [self.record])
        for amount in [1.25, -1, 2**256]:
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, "uint256"):
                save_transfers(self.path, [replace(self.record, log_index=1, raw_amount=amount)])
        self.assertEqual(self.count(), 1)

    def test_cli_accepts_range_and_database_path(self):
        with (
            patch("sys.argv", ["chaintrace", "collect-token-logs", "291", "292", "--db", str(self.path)]),
            patch("chaintrace.storage.collect_transfers") as collect,
        ):
            main()
        collect.assert_called_once_with(291, 292, self.path)
