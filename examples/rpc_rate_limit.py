"""Offline M3 HTTP 429 cases; reuses the CLI/temporary-DB experiment driver."""

from urllib.error import HTTPError

from rpc_timeout_retry import run_case, synthetic_logs


def limited():
    return HTTPError("https://offline.invalid", 429, "Too Many Requests", {"Retry-After": "5"}, None)


if __name__ == "__main__":
    print("OFFLINE SIMULATION: HTTP 429, synthetic data, no network or real waits, temporary DBs")
    run_case("429 Retry-After 5 then success", [limited(), synthetic_logs()], 0, 2, [5])
    run_case("three HTTP 429 responses", [limited(), limited(), limited()], 1, 3, [5, 5])
    run_case("timeout then 429 then success", [TimeoutError(), limited(), synthetic_logs()], 0, 3, [1, 5])
    print("Checks passed: Retry-After respected; timeout and 429 share one attempt budget")
