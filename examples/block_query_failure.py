"""Offline M3 experiment: empty query success versus HTTP 403 failure.

Uses the real CLI, RPC response handling and log-query code. Only configuration
and HTTP transport are replaced; no network request or progress write occurs.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

from chaintrace import main


def response(result: object) -> io.StringIO:
    return io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}))


def run_case(fail: bool) -> tuple[int, str, str]:
    url = "https://offline.invalid"
    block = {"number": "0x123", "hash": "0x" + "b" * 64, "timestamp": "0x456"}
    replies = [response("0x1"), response(block)]
    replies.append(HTTPError(url, 403, "Forbidden", None, None) if fail else response([]))
    output, error = io.StringIO(), io.StringIO()
    code = 0
    with (
        patch("sys.argv", ["chaintrace", "token-logs", "291"]),
        patch("chaintrace.transfer.rpc_url", return_value=url),
        patch("chaintrace.rpc.urlopen", side_effect=replies) as transport,
        redirect_stdout(output), redirect_stderr(error),
    ):
        try:
            main()
        except SystemExit as exc:
            code = exc.code
    methods = [json.loads(call.args[0].data)["method"] for call in transport.call_args_list]
    assert methods == ["eth_chainId", "eth_getBlockByNumber", "eth_getLogs"]
    print("Case:", "HTTP 403" if fail else "successful empty list")
    print("CLI exit code:", code)
    for line in output.getvalue().splitlines():
        if line.startswith(("USDC Transfer logs:", "No matching")):
            print(line)
    if error.getvalue():
        print(error.getvalue().strip())
    return code, output.getvalue(), error.getvalue()


if __name__ == "__main__":
    print("OFFLINE SIMULATION: no network, database or checkpoint writes")
    code, output, error = run_case(fail=False)
    assert code == 0 and "USDC Transfer logs: 0" in output and not error
    code, output, error = run_case(fail=True)
    assert code == 1 and "403" in error and "USDC Transfer logs:" not in output
    print("Checks passed: a query failure is not reported as an empty success")
