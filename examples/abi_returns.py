"""Offline M2 experiment: zero-valued ABI word versus empty return data.

Run: uv run --locked python examples/abi_returns.py
This deliberately simulates RPC results; it makes no network request.
"""

from unittest.mock import patch

from chaintrace.token import read_uint256


def main() -> None:
    print("SIMULATION ONLY: no network request or real token balance query")
    cases = [
        ("32-byte zero word", "0x" + "0" * 64),
        ("Empty return data", "0x"),
    ]
    for label, raw in cases:
        print(f"\n{label}")
        print(f"Raw: {raw}")
        with patch("chaintrace.token.rpc_call", return_value=raw):
            try:
                value = read_uint256("https://rpc.example", "0x70a08231", "0x123")
            except ValueError as exc:
                print(f"Rejected: {exc}")
            else:
                print(f"Decoded integer: {value}")


if __name__ == "__main__":
    main()
