import platform
import sys
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainTrace learning experiments")
    parser.add_argument("command", nargs="?", choices=["network", "balance", "transaction", "token-balance", "token-info", "token-allowance", "token-transfers", "token-logs", "collect-token-logs"])
    parser.add_argument("target", nargs="?", help="Public address, transaction hash, or decimal start block (log commands)")
    parser.add_argument("spender", nargs="?", help="Spender address (token-allowance) or inclusive end block (log commands)")
    parser.add_argument("--db", type=Path, help="SQLite path for collect-token-logs (default: project data/chaintrace.sqlite3)")
    args = parser.parse_args()
    if args.spender and args.command not in {"token-allowance", "token-logs", "collect-token-logs"}:
        parser.error("此命令不接受第二个参数")
    if args.db is not None and args.command != "collect-token-logs":
        parser.error("--db 仅适用于 collect-token-logs")
    if args.command in {"network", "balance", "transaction", "token-balance", "token-info", "token-allowance", "token-transfers", "token-logs", "collect-token-logs"}:
        from chaintrace.rpc import show_balance, show_network, show_transaction

        try:
            if args.command in {"token-logs", "collect-token-logs"}:
                from chaintrace.transfer import show_block_transfers

                if not args.target or not args.target.isascii() or not args.target.isdecimal():
                    parser.error("日志命令需要一个非负十进制区块号")
                if args.spender is not None and (not args.spender.isascii() or not args.spender.isdecimal()):
                    parser.error("结束区块必须为非负十进制整数")
                end_block = int(args.spender) if args.spender is not None else None
                if args.command == "collect-token-logs":
                    from chaintrace.storage import DEFAULT_DB, collect_transfers

                    collect_transfers(int(args.target), end_block, args.db if args.db is not None else DEFAULT_DB)
                else:
                    show_block_transfers(int(args.target), end_block)
            elif args.command == "token-transfers":
                from chaintrace.transfer import show_transfers

                if not args.target:
                    parser.error("token-transfers 命令需要一个交易哈希")
                show_transfers(args.target)
            elif args.command == "token-allowance":
                from chaintrace.token import show_token_allowance

                if not args.target or not args.spender:
                    parser.error("token-allowance 命令需要持有者和被授权者两个地址")
                show_token_allowance(args.target, args.spender)
            elif args.command == "token-info":
                from chaintrace.token import show_token_info

                if args.target or args.spender:
                    parser.error("token-info 命令不需要地址")
                show_token_info()
            elif args.command == "token-balance":
                from chaintrace.token import show_token_balance

                if not args.target:
                    parser.error("token-balance 命令需要一个公开持有者地址")
                show_token_balance(args.target)
            elif args.command == "balance":
                if not args.target:
                    parser.error("balance 命令需要一个公开地址")
                show_balance(args.target)
            elif args.command == "transaction":
                if not args.target:
                    parser.error("transaction 命令需要一个交易哈希")
                show_transaction(args.target)
            else:
                if args.target:
                    parser.error("network 命令不需要地址")
                show_network()
        except ValueError as exc:
            parser.exit(1, f"查询失败：{exc}\n")
        return
    print("ChainTrace environment ready")
    print(f"Python: {platform.python_version()}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Virtual environment: {sys.prefix != sys.base_prefix}")
