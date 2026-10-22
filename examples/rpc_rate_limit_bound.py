"""Offline M3 example: stop when server wait exceeds the local budget."""

from urllib.error import HTTPError

from rpc_timeout_retry import run_case


if __name__ == "__main__":
    print("OFFLINE SIMULATION: no network or real waits, temporary DB")
    print("Server Retry-After: 120 seconds | Local maximum wait: 30 seconds")
    error = HTTPError("https://offline.invalid", 429, "Too Many Requests", {"Retry-After": "120"}, None)
    run_case("server wait exceeds local budget", [error], 1, 1, [])
    print("Checks passed: no early retry, no wait, no database write")
