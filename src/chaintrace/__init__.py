import platform
import sys


def main() -> None:
    print("ChainTrace environment ready")
    print(f"Python: {platform.python_version()}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Virtual environment: {sys.prefix != sys.base_prefix}")
