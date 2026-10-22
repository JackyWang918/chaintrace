"""M1: read public Ethereum data through JSON-RPC."""

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv


READ_RETRY_METHODS = frozenset({
    "eth_chainId", "eth_blockNumber", "eth_getBalance",
    "eth_getTransactionByHash", "eth_getTransactionReceipt",
    "eth_call", "eth_getBlockByNumber", "eth_getLogs",
})
MAX_RETRY_WAIT_SECONDS = 30


class _RPCTimeout(ValueError):
    """Only a recognized transport timeout is eligible for this experiment."""


class _RPCRateLimited(ValueError):
    def __init__(self, retry_after: str | None):
        super().__init__("HTTP 429 限流")
        self.retry_after = retry_after


def _retry_after_seconds(raw: str | None) -> int | None:
    if raw is None:
        return None
    value = raw.strip()
    try:
        if re.fullmatch(r"[0-9]+", value):
            return int(value)
        moment = parsedate_to_datetime(value)
        if moment.tzinfo is None:
            # The obsolete HTTP asctime format has no zone but means UTC.
            moment = moment.replace(tzinfo=timezone.utc)
        return max(0, math.ceil((moment - datetime.now(timezone.utc)).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        raise ValueError("RPC HTTP 429 的 Retry-After 格式无效，本次停止") from None


def rpc_call(url: str, method: str, params: list[object] | None = None) -> object:
    # Explicit read allowlist: do not carry this retry policy into future writes.
    max_attempts = 3 if method in READ_RETRY_METHODS else 1
    for attempt in range(1, max_attempts + 1):
        try:
            return _rpc_call_once(url, method, params)
        except (_RPCTimeout, _RPCRateLimited) as exc:
            reason = "HTTP 429 限流" if isinstance(exc, _RPCRateLimited) else "请求超时"
            if attempt == max_attempts:
                raise ValueError(f"RPC {reason}，已尝试 {attempt} 次，本次查询失败") from None
            delay = attempt
            if isinstance(exc, _RPCRateLimited):
                requested = _retry_after_seconds(exc.retry_after)
                if requested is not None:
                    delay = max(delay, requested)
                if delay > MAX_RETRY_WAIT_SECONDS:
                    raise ValueError(
                        f"RPC HTTP 429 要求等待超过本实验 {MAX_RETRY_WAIT_SECONDS} 秒上限，本次停止"
                    ) from None
            print(
                f"RPC {method} 第 {attempt} 次{reason}，{delay} 秒后重试（最多 {max_attempts} 次尝试）",
                file=sys.stderr,
            )
            sleep(delay)


def _rpc_call_once(url: str, method: str, params: list[object] | None = None) -> object:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ChainTrace-M1/0.1"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = json.load(response)
    except HTTPError as exc:
        code = exc.code
        retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
        exc.close()
        if code == 429:
            raise _RPCRateLimited(retry_after) from None
        raise ValueError(f"RPC HTTP 错误：{code}，本轮不自动重试该状态码") from None
    except TimeoutError:
        raise _RPCTimeout("RPC 请求超时") from None
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise _RPCTimeout("RPC 请求超时") from None
        raise ValueError("RPC 连接失败，请检查网络和 ETH_RPC_URL") from None
    except OSError:
        raise ValueError("RPC 连接失败，请检查网络和 ETH_RPC_URL") from None
    except (ValueError, UnicodeError):
        raise ValueError("RPC 返回了无法解析的 JSON") from None

    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or body.get("id") != 1:
        raise ValueError("RPC 返回格式不符合预期")
    if "error" in body:
        raise ValueError("RPC 返回了应用层错误，本次查询未成功")
    if "result" not in body:
        raise ValueError("RPC 缺少 result 字段")
    return body["result"]


def quantity(raw: object) -> int:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise ValueError("RPC 未返回十六进制整数")
    try:
        value = int(raw, 16)
    except ValueError:
        raise ValueError("RPC 返回的十六进制整数无效") from None
    if value < 0:
        raise ValueError("RPC 返回了负数")
    return value


def read_quantity(url: str, method: str, params: list[object] | None = None) -> tuple[str, int]:
    raw = rpc_call(url, method, params)
    value = quantity(raw)
    return str(raw), value


def rpc_url() -> str:
    # Existing shell variables take precedence over the local .env file.
    load_dotenv()
    url = os.getenv("ETH_RPC_URL", "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("请在项目 .env 中配置有效的 ETH_RPC_URL（参照 .env.example）")
    return url


def checked_mainnet(url: str) -> tuple[str, int]:
    chain_raw, chain_id = read_quantity(url, "eth_chainId")
    if chain_id != 1:
        raise ValueError(f"本实验预期 Ethereum Mainnet（链 ID 1），节点返回 {chain_id}，请检查 RPC 配置")
    return chain_raw, chain_id


def format_units(amount: int, decimals: int) -> str:
    if amount < 0 or not 0 <= decimals <= 255:
        raise ValueError("金额必须为非负整数，decimals 必须在 0 到 255 之间")
    whole, fraction = divmod(amount, 10**decimals)
    if fraction == 0:
        return str(whole)
    return f"{whole}.{fraction:0{decimals}d}".rstrip("0")


def format_eth(wei: int) -> str:
    return format_units(wei, 18)


def show_network() -> None:
    url = rpc_url()

    chain_raw, chain_id = checked_mainnet(url)
    print(f"Chain ID: {chain_id} (RPC raw: {chain_raw})")
    block_raw, block_number = read_quantity(url, "eth_blockNumber")
    print("Network: Ethereum Mainnet")
    print(f"Latest block: {block_number} (RPC raw: {block_raw})")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify block: https://etherscan.io/block/{block_number}")


def show_balance(address: str) -> None:
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        raise ValueError("地址格式错误：应为 0x 开头、后接 40 位十六进制字符")
    url = rpc_url()
    _, chain_id = checked_mainnet(url)
    block_raw, block_number = read_quantity(url, "eth_blockNumber")
    balance_raw, wei = read_quantity(url, "eth_getBalance", [address, block_raw])
    print(f"Chain ID: {chain_id} (Ethereum Mainnet)")
    print(f"Address: {address}")
    print(f"Block: {block_number} (RPC raw: {block_raw})")
    print(f"Balance: {wei} wei (RPC raw: {balance_raw})")
    print(f"Balance: {format_eth(wei)} ETH")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify address: https://etherscan.io/address/{address}")


def show_transaction(tx_hash: str) -> None:
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
        raise ValueError("交易哈希格式错误：应为 0x 开头、后接 64 位十六进制字符")
    url = rpc_url()
    checked_mainnet(url)
    tx = rpc_call(url, "eth_getTransactionByHash", [tx_hash])
    print("Network: Ethereum Mainnet (Chain ID: 1)")
    print(f"Transaction: {tx_hash}")
    if tx is None:
        print("Result: transaction not found by this node; execution status unknown")
        return
    if not isinstance(tx, dict) or str(tx.get("hash", "")).lower() != tx_hash.lower():
        raise ValueError("RPC 返回的交易对象或哈希不符合预期")
    for field in ("from", "to", "value", "nonce", "gas", "input", "blockNumber", "blockHash"):
        if field not in tx:
            raise ValueError(f"RPC 交易缺少字段：{field}")
    value = quantity(tx["value"])
    print(f"From: {tx['from']}")
    print(f"To: {tx['to']}")
    print(f"Requested value: {value} wei = {format_eth(value)} ETH")
    print(f"Nonce: {quantity(tx['nonce'])}")
    print(f"Gas limit (request): {quantity(tx['gas'])}")
    print(f"Input data: {tx['input']}")

    receipt = rpc_call(url, "eth_getTransactionReceipt", [tx_hash])
    if receipt is None:
        if tx["blockNumber"] is None:
            print("Receipt: not available; node reports transaction as pending")
        else:
            print("Receipt: not available despite a reported block; execution status unknown, retry later")
        return
    if not isinstance(receipt, dict):
        raise ValueError("RPC 返回的回执格式不符合预期")
    if (
        str(receipt.get("transactionHash", "")).lower() != tx_hash.lower()
        or not receipt.get("blockHash")
        or receipt["blockHash"] != tx["blockHash"]
        or receipt.get("blockNumber") != tx["blockNumber"]
    ):
        raise ValueError("交易与回执的哈希或区块不一致，请重新查询")
    status = quantity(receipt.get("status"))
    if status not in {0, 1}:
        raise ValueError("回执执行状态不是 0 或 1")
    gas_used = quantity(receipt.get("gasUsed"))
    gas_price = quantity(receipt.get("effectiveGasPrice"))
    fee = gas_used * gas_price
    print(f"Block: {quantity(receipt['blockNumber'])}")
    print(f"Block hash: {receipt['blockHash']}")
    print(f"Execution: {'SUCCESS' if status == 1 else 'FAILED'} (receipt status={status})")
    print(f"Gas used (receipt): {gas_used}")
    print(f"Effective gas price: {gas_price} wei/gas")
    print(f"Execution fee: {gas_used} * {gas_price} = {fee} wei = {format_eth(fee)} ETH")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify transaction: https://etherscan.io/tx/{tx_hash}")
