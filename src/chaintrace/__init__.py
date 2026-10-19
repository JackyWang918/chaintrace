import platform
import sys
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainTrace learning experiments")
    parser.add_argument("command", nargs="?", choices=["network", "balance", "transaction", "token-balance", "token-info", "token-allowance", "token-transfers", "token-logs"])
    parser.add_argument("target", nargs="?", help="Public address, transaction hash, or decimal block number (token-logs)")
    parser.add_argument("spender", nargs="?", help="Spender address for token-allowance")
    args = parser.parse_args()
    if args.spender and args.command != "token-allowance":
        parser.error("此命令不接受第二个地址")
    if args.command in {"network", "balance", "transaction", "token-balance", "token-info", "token-allowance", "token-transfers", "token-logs"}:
        from chaintrace.rpc import show_balance, show_network, show_transaction

        try:
            if args.command == "token-logs":
                from chaintrace.transfer import show_block_transfers

                if not args.target or not args.target.isascii() or not args.target.isdecimal():
                    parser.error("token-logs 命令需要一个非负十进制区块号")
                show_block_transfers(int(args.target))
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
