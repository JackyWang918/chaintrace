"""M3: inspect USDC Transfer logs in one receipt or one block."""

import re
from datetime import datetime, timezone

from chaintrace.rpc import checked_mainnet, format_units, quantity, rpc_call, rpc_url
from chaintrace.token import DECIMALS_SELECTOR, USDC_CONTRACT, read_uint256

# keccak256("Transfer(address,address,uint256)"); this is an event identifier.
# https://eips.ethereum.org/EIPS/eip-20#events
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def decode_transfer(log: dict) -> tuple[str, str, int] | None:
    """Ignore other contracts/events; reject malformed matching USDC events."""
    if str(log.get("address", "")).lower() != USDC_CONTRACT.lower():
        return None
    topics = log.get("topics")
    if not isinstance(topics, list):
        raise ValueError("USDC 日志缺少有效 topics")
    if not topics or str(topics[0]).lower() != TRANSFER_TOPIC:
        return None
    if len(topics) != 3:
        raise ValueError("USDC Transfer 应有三个 topics")
    addresses = []
    for word in topics[1:]:
        if not isinstance(word, str) or not re.fullmatch(r"0x0{24}[0-9a-fA-F]{40}", word):
            raise ValueError("Transfer 地址不是有效的 ABI address")
        addresses.append("0x" + word[-40:].lower())
    data = log.get("data")
    if not isinstance(data, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", data):
        raise ValueError("Transfer 金额不是有效的 32 字节整数，不能当成零")
    return addresses[0], addresses[1], int(data, 16)


def show_block_transfers(block_number: int) -> None:
    """Read one existing block; retain every log, including repeated tx hashes."""
    if block_number < 0:
        raise ValueError("区块号必须为非负整数")
    url = rpc_url()
    checked_mainnet(url)
    block_raw = hex(block_number)
    block = rpc_call(url, "eth_getBlockByNumber", [block_raw, False])
    if block is None:
        raise ValueError("节点未返回该区块，不能当成该区块没有转账")
    if (
        not isinstance(block, dict)
        or quantity(block.get("number")) != block_number
        or not isinstance(block.get("hash"), str)
        or not re.fullmatch(r"0x[0-9a-fA-F]{64}", block["hash"])
    ):
        raise ValueError("节点返回的区块编号或哈希不符合预期")
    timestamp = quantity(block.get("timestamp"))
    logs = rpc_call(url, "eth_getLogs", [{
        "fromBlock": block_raw,
        "toBlock": block_raw,
        "address": USDC_CONTRACT,
        "topics": [TRANSFER_TOPIC],
    }])
    if not isinstance(logs, list):
        raise ValueError("节点未返回有效日志列表，不能当成零条")
    transfers = []
    seen_indices = set()
    for log in logs:
        if not isinstance(log, dict):
            raise ValueError("节点返回的日志格式错误")
        if (
            quantity(log.get("blockNumber")) != block_number
            or log.get("blockHash") != block["hash"]
            or log.get("removed") is not False
        ):
            raise ValueError("日志已移除或区块归属不一致，请重新查询")
        tx_hash = log.get("transactionHash")
        if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
            raise ValueError("日志缺少有效交易哈希")
        decoded = decode_transfer(log)
        if decoded is None:
            raise ValueError("节点返回了不符合 USDC Transfer 筛选条件的日志")
        index = quantity(log.get("logIndex"))
        if index in seen_indices:
            raise ValueError("节点返回重复 logIndex，停止处理，不静默丢弃")
        seen_indices.add(index)
        transfers.append((index, tx_hash, decoded))
    transfers.sort(key=lambda item: item[0])
    print("Network: Ethereum Mainnet (Chain ID: 1)")
    print(f"Block range (inclusive): {block_number}..{block_number}")
    print(f"Block hash: {block['hash']}")
    print(f"Block timestamp (Unix seconds): {timestamp}")
    print(f"Token contract: {USDC_CONTRACT}")
    print(f"USDC Transfer logs: {len(transfers)}")
    print(f"Distinct transactions with matching logs: {len({item[1] for item in transfers})}")
    if transfers:
        for index, tx_hash, (sender, recipient, amount) in transfers:
            print(f"Log index: {index} | Transaction: {tx_hash}")
            print(f"  Token from: {sender} | Token to: {recipient}")
            print(f"  Raw amount: {amount} (token base units, not wei)")
    else:
        print("No matching USDC Transfer logs; this is not a zero-amount transfer")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify block: https://etherscan.io/block/{block_number}")
    print("Raw amounts only; decimals is not queried by this experiment")
    print("Read-only; no database, retries, or finality/reorg recovery")


def show_transfers(tx_hash: str) -> None:
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
    print(f"Transaction from (caller): {tx.get('from')}")
    print(f"Transaction to (called address): {tx.get('to')}")
    receipt = rpc_call(url, "eth_getTransactionReceipt", [tx_hash])
    if receipt is None:
        print("Receipt: not available; execution status unknown, retry later")
        return
    if (
        not isinstance(receipt, dict)
        or str(receipt.get("transactionHash", "")).lower() != tx_hash.lower()
        or not receipt.get("blockHash")
        or receipt["blockHash"] != tx.get("blockHash")
        or receipt.get("blockNumber") != tx.get("blockNumber")
    ):
        raise ValueError("交易与回执的哈希或区块不一致，请重新查询")
    status = quantity(receipt.get("status"))
    if status not in {0, 1}:
        raise ValueError("回执执行状态不是 0 或 1")
    logs = receipt.get("logs")
    if not isinstance(logs, list):
        raise ValueError("回执未返回有效 logs，不能当成没有转账")
    if status == 0 and logs:
        raise ValueError("失败回执包含日志，与预期不符，停止解析")
    transfers = []
    for log in logs:
        if not isinstance(log, dict):
            raise ValueError("回执日志格式错误")
        decoded = decode_transfer(log)
        if decoded is None:
            continue
        if (
            log.get("removed") is not False
            or log.get("transactionHash") != receipt["transactionHash"]
            or log.get("blockHash") != receipt["blockHash"]
            or log.get("blockNumber") != receipt["blockNumber"]
        ):
            raise ValueError("日志已移除或与回执不一致，请重新查询")
        transfers.append((quantity(log.get("logIndex")), log, decoded))
    print(f"Block: {quantity(receipt['blockNumber'])}")
    print(f"Block hash: {receipt['blockHash']}")
    print(f"Execution: {'SUCCESS' if status else 'FAILED'} (receipt status={status})")
    print(f"USDC Transfer logs: {len(transfers)}")
    if transfers:
        decimals = read_uint256(url, DECIMALS_SELECTOR, receipt["blockNumber"])
        if not 0 <= decimals <= 255:
            raise ValueError("合约 decimals 超出 uint8 范围，停止换算")
        print(f"Decimals (contract at receipt block): {decimals}")
        for index, log, (sender, recipient, amount) in transfers:
            print(f"Log index (within block): {index}")
            print(f"  Emitting contract: {log['address']}")
            print(f"  Token from: {sender}")
            print(f"  Token to: {recipient}")
            print(f"  Raw amount: {amount} (token base units, not wei)")
            print(f"  Amount: {format_units(amount, decimals)} USDC")
            print(f"  Raw topics: {log['topics']}")
            print(f"  Raw data: {log['data']}")
    else:
        print("No matching USDC Transfer logs; this is not a zero-amount transfer")
    print(f"Queried at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Verify transaction: https://etherscan.io/tx/{tx_hash}#eventlog")
    print("Read-only; no transaction sent; finality is not checked")
