"""Offline M3 experiment: conflicting content rolls back the entire batch.

All records are synthetic. Uses a temporary database, never the project DB.
"""

import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

from chaintrace.storage import save_transfers
from chaintrace.token import USDC_CONTRACT
from chaintrace.transfer import TransferRecord


def snapshot(path: Path) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT * FROM transfers ORDER BY log_index").fetchall()


def main() -> None:
    print("OFFLINE SIMULATION: synthetic logs, temporary DB, no network")
    base = TransferRecord(
        chain_id=1, token_contract=USDC_CONTRACT.lower(), block_number=291,
        block_hash="0x" + "b" * 64, transaction_hash="0x" + "a" * 64,
        log_index=0, sender="0x" + "1" * 40, recipient="0x" + "3" * 40,
        raw_amount=100, block_timestamp=1000,
    )
    with tempfile.TemporaryDirectory(prefix="chaintrace-conflict-") as folder:
        path = Path(folder) / "logs.sqlite3"
        original = [replace(base, log_index=index) for index in range(131)]
        assert save_transfers(path, original) == (131, 0, 131)
        before = snapshot(path)
        print("Before batch: 131 stored logs")
        new_rows = [replace(base, log_index=index) for index in (131, 132, 133)]
        conflict = replace(base, raw_amount=200)
        print("Batch order: 3 new logs, then same identity with amount 100 -> 200")
        try:
            save_transfers(path, [*new_rows, conflict])
        except ValueError as exc:
            assert "内容冲突" in str(exc)
            print("Expected error:", exc)
        else:
            raise AssertionError("Conflicting content was incorrectly accepted")
        after = snapshot(path)
        assert after == before, "Rollback must preserve every original field"
        with sqlite3.connect(path) as connection:
            new_count = connection.execute(
                "SELECT COUNT(*) FROM transfers WHERE log_index IN (131,132,133)"
            ).fetchone()[0]
            saved_amount = connection.execute(
                "SELECT raw_amount FROM transfers WHERE log_index=0"
            ).fetchone()[0]
        assert new_count == 0 and saved_amount == "100"
        print("After failed batch:", len(after), "stored logs")
        print("New logs remaining:", new_count)
        print("Original amount:", saved_amount)
        print("Checks passed: all 131 original rows unchanged; 3 new rows rolled back")
    print("Temporary DB removed; project database was not opened")


if __name__ == "__main__":
    main()
