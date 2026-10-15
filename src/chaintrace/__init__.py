import platform
import sys
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainTrace learning experiments")
    parser.add_argument("command", nargs="?", choices=["network", "balance", "transaction"])
    parser.add_argument("target", nargs="?", help="Public address (balance) or transaction hash (transaction)")
    args = parser.parse_args()
    if args.command in {"network", "balance", "transaction"}:
        from chaintrace.rpc import show_balance, show_network, show_transaction

        try:
            if args.command == "balance":
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
