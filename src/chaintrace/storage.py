"""M3 minimal SQLite persistence: identical logs are idempotent, conflicts fail."""

import sqlite3
from contextlib import closing
from pathlib import Path

from chaintrace.transfer import TransferRecord, read_block_transfers


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "chaintrace.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transfers (
    chain_id INTEGER NOT NULL,
    token_contract TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    block_hash TEXT NOT NULL,
    transaction_hash TEXT NOT NULL,
    log_index INTEGER NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    raw_amount TEXT NOT NULL,
    block_timestamp INTEGER NOT NULL,
    PRIMARY KEY (chain_id, block_hash, log_index)
)
"""
COLUMNS = """chain_id, token_contract, block_number, block_hash,
transaction_hash, log_index, sender, recipient, raw_amount, block_timestamp"""


def save_transfers(path: Path, records: list[TransferRecord]) -> tuple[int, int, int]:
    """Commit one complete batch; roll back its inserts on any conflict/error."""
    inserted = existing = 0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(SCHEMA)
                for item in records:
                    if type(item.raw_amount) is not int or not 0 <= item.raw_amount < 2**256:
                        raise ValueError("原始金额必须为 uint256 整数，不能使用浮点数")
                    values = (
                        item.chain_id, item.token_contract.lower(), item.block_number,
                        item.block_hash.lower(), item.transaction_hash.lower(),
                        item.log_index, item.sender.lower(), item.recipient.lower(),
                        str(item.raw_amount), item.block_timestamp,
                    )
                    key = (values[0], values[3], values[5])
                    saved = connection.execute(
                        f"SELECT {COLUMNS} FROM transfers "
                        "WHERE chain_id=? AND block_hash=? AND log_index=?", key,
                    ).fetchone()
                    if saved is not None:
                        if saved != values:
                            raise ValueError(
                                f"同一日志标识内容冲突：chain_id={key[0]}, "
                                f"block_hash={key[1]}, log_index={key[2]}；本批写入已回滚"
                            )
                        existing += 1
                        continue
                    connection.execute(
                        f"INSERT INTO transfers ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        values,
                    )
                    inserted += 1
                total = connection.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]
        return inserted, existing, total
    except (sqlite3.Error, OSError) as exc:
        raise ValueError(f"SQLite 写入失败，本批未提交：{exc}") from None


def collect_transfers(start: int, end: int | None = None, path: Path = DEFAULT_DB) -> None:
    # All RPC responses and logs must pass validation before the DB is opened.
    _, _, records = read_block_transfers(start, end)
    inserted, existing, total = save_transfers(path, records)
    print("Network: Ethereum Mainnet (Chain ID: 1)")
    print(f"Block range (inclusive): {start}..{end if end is not None else start}")
    print(f"Database: {path.resolve()}")
    print(f"Fetched logs: {len(records)}")
    print(f"Inserted: {inserted}")
    print(f"Already stored (identical): {existing}")
    print(f"Total stored logs (entire database): {total}")
    print("Batch committed; no chain transaction sent; no checkpoint or reorg recovery")
