"""Offline M3 experiment: no logs versus one valid zero-amount log.

All RPC/configuration entry points used by show_transfers are replaced below.
The hashes and addresses are synthetic; no network request is made.
"""

import io
from contextlib import redirect_stdout
from unittest.mock import patch

from chaintrace.token import USDC_CONTRACT
from chaintrace.transfer import TRANSFER_TOPIC, show_transfers


def run_case(label: str, logs: list[dict]) -> str:
    tx_hash = "0x" + "a" * 64
    block_hash = "0x" + "b" * 64
    tx = {
        "hash": tx_hash, "from": "0x" + "2" * 40, "to": USDC_CONTRACT,
        "blockNumber": "0x123", "blockHash": block_hash,
    }
    receipt = {
        "transactionHash": tx_hash, "blockNumber": "0x123",
        "blockHash": block_hash, "status": "0x1", "logs": logs,
    }
    output = io.StringIO()
    with (
        patch("chaintrace.transfer.rpc_url", return_value="https://offline.invalid"),
        patch("chaintrace.transfer.checked_mainnet"),
        patch("chaintrace.transfer.rpc_call", side_effect=[tx, receipt]),
        patch("chaintrace.transfer.read_uint256", return_value=6),
        redirect_stdout(output),
    ):
        show_transfers(tx_hash)
    result = output.getvalue()
    print(label)
    # Show the relevant real parser output, omitting synthetic explorer links.
    for line in result.splitlines():
        if line.startswith(("Execution:", "USDC Transfer logs:", "No matching", "  Raw amount:", "  Amount:")):
            print(line)
    return result


def main() -> None:
    print("OFFLINE SIMULATION: synthetic receipts; no network or transactions")
    empty = run_case("Case 1: successful receipt, no logs", [])
    zero_log = {
        "address": USDC_CONTRACT,
        "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + "1" * 40,
                   "0x" + "0" * 24 + "3" * 40],
        "data": "0x" + "0" * 64,
        "transactionHash": "0x" + "a" * 64,
        "blockHash": "0x" + "b" * 64,
        "blockNumber": "0x123", "logIndex": "0x0", "removed": False,
    }
    zero = run_case("Case 2: successful receipt, one zero-amount Transfer", [zero_log])
    assert "USDC Transfer logs: 0" in empty and "  Amount:" not in empty
    assert "USDC Transfer logs: 1" in zero and "  Amount: 0 USDC" in zero
    print("Checks passed: absence of a log is distinct from a logged amount of zero")


if __name__ == "__main__":
    main()
