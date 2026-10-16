"""M2 first experiment: two read-only calls to the mainnet USDC contract."""

import re
from datetime import datetime, timezone

from chaintrace.rpc import checked_mainnet, format_units, read_quantity, rpc_call, rpc_url

# Asset identity is (chain ID 1, this address), not the display name.
# Source: https://developers.circle.com/stablecoins/usdc-contract-addresses
USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# First four bytes of keccak256("decimals()") and keccak256("balanceOf(address)").
# These are ABI method selectors, not transaction signatures.
DECIMALS_SELECTOR = "0x313ce567"
BALANCE_OF_SELECTOR = "0x70a08231"


def read_uint256(url: str, data: str, block: str) -> int:
    raw = rpc_call(url, "eth_call", [{"to": USDC_CONTRACT, "data": data}, block])
    # An ABI uint is one 32-byte word. Empty data must not become balance zero.
    if not isinstance(raw, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", raw):
        raise ValueError("合约未返回一个有效的 32 字节 ABI 整数，不能将其视为余额 0")
    return int(raw, 16)


def show_token_balance(holder: str) -> None:
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", holder):
        raise ValueError("持有者地址格式错误：应为 0x 开头、后接 40 位十六进制字符")
    url = rpc_url()
    checked_mainnet(url)
    block_raw, block_number = read_quantity(url, "eth_blockNumber")
    decimals = read_uint256(url, DECIMALS_SELECTOR, block_raw)
    if not 0 <= decimals <= 255:
        raise ValueError("合约 decimals 超出 uint8 范围，停止换算")
    # ABI encodes an address as 20 bytes padded on the left to 32 bytes.
    data = BALANCE_OF_SELECTOR + holder[2:].lower().zfill(64)
    raw_balance = read_uint256(url, data, block_raw)
    print("Network: Ethereum Mainnet (Chain ID: 1)")
    print("Asset: USDC (configured sample; name is not queried)")
    print(f"Token contract: {USDC_CONTRACT}")
    print(f"Holder: {holder}")
    print(f"Block: {block_number}")
    print(f"Decimals (contract): {decimals}")
    print(f"Raw token balance: {raw_balance} (token base units, not wei)")
    print(f"Token balance: {format_units(raw_balance, decimals)} USDC")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify holder: https://etherscan.io/token/{USDC_CONTRACT}?a={holder}")
