"""Offline M3 timeout retries through the real CLI and SQLite write path.

HTTP responses/timeouts and sleep are simulated. Databases are temporary.
"""

import io
import json
import sqlite3
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import call, patch
from urllib.error import HTTPError, URLError

from chaintrace import main
from chaintrace.storage import save_transfers
from chaintrace.token import USDC_CONTRACT
from chaintrace.transfer import TRANSFER_TOPIC


def response(result):
    return io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}))


def synthetic_logs():
    return [{
        "address": USDC_CONTRACT, "blockHash": "0x" + "b" * 64,
        "blockNumber": "0x123", "transactionHash": "0x" + "a" * 64,
        "logIndex": hex(index), "removed": False,
        "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + "1" * 40,
                   "0x" + "0" * 24 + "3" * 40],
        "data": "0x" + format(100 + index, "064x"),
    } for index in range(131)]


def run_case(name, results, expected_exit, expected_attempts):
    attempts = 0
    log_payloads = []

    def transport(request, timeout):
        nonlocal attempts
        payload = json.loads(request.data)
        method = payload["method"]
        if method == "eth_chainId":
            return response("0x1")
        if method == "eth_getBlockByNumber":
            number = int(payload["params"][0], 16)
            return response({"number": hex(number), "hash": "0x" + ("b" if number == 291 else "c") * 64,
                             "timestamp": hex(1000 + (number - 291) * 12)})
        assert method == "eth_getLogs"
        log_payloads.append(payload)
        result = results[attempts]
        attempts += 1
        if isinstance(result, Exception):
            raise result
        return response(result)

    with tempfile.TemporaryDirectory(prefix="chaintrace-retry-") as folder:
        path = Path(folder) / "logs.sqlite3"
        out, err = io.StringIO(), io.StringIO()
        exit_code = 0
        with (
            patch("sys.argv", ["chaintrace", "collect-token-logs", "291", "292", "--db", str(path)]),
            patch("chaintrace.transfer.rpc_url", return_value="https://offline.invalid"),
            patch("chaintrace.rpc.urlopen", side_effect=transport),
            patch("chaintrace.rpc.sleep") as wait,
            patch("chaintrace.storage.save_transfers", wraps=save_transfers) as save,
            redirect_stdout(out), redirect_stderr(err),
        ):
            try:
                main()
            except SystemExit as exc:
                exit_code = exc.code
        assert exit_code == expected_exit and attempts == expected_attempts
        assert all(item == log_payloads[0] for item in log_payloads)
        expected_waits = [call(1), call(2)] if expected_attempts == 3 else []
        assert wait.call_args_list == expected_waits
        assert save.call_count == (1 if exit_code == 0 else 0)
        if exit_code == 0:
            with sqlite3.connect(path) as connection:
                count = connection.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]
            assert count == 131
        else:
            assert not path.exists()
            assert "Fetched logs:" not in out.getvalue()
            count = 0
        print("Case:", name)
        print("eth_getLogs requests:", attempts)
        print("Retry waits (seconds, simulated):", [item.args[0] for item in wait.call_args_list])
        print("Database write batches:", save.call_count)
        print("CLI exit code:", exit_code)
        print("Rows stored:", count, "| Database exists:", path.exists())
        for line in err.getvalue().splitlines():
            print(line)


if __name__ == "__main__":
    print("OFFLINE SIMULATION: synthetic data, no network, no real waits, temporary DBs")
    run_case("two timeouts then success", [TimeoutError(), URLError(TimeoutError()), synthetic_logs()], 0, 3)
    run_case("three timeouts", [TimeoutError(), TimeoutError(), TimeoutError()], 1, 3)
    run_case("HTTP 403 stops immediately", [HTTPError("https://offline.invalid", 403, "Forbidden", None, None)], 1, 1)
    print("Checks passed: bounded read retries; failed acquisition never opens the database")
