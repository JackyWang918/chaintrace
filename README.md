# ChainTrace（链迹）

使用 Python 学习 EVM 链上数据，逐步构建 ERC-20 地址转账监控系统。
当前处于 M1 环境准备阶段，尚未配置 RPC 或进行链上查询。

## 环境

- 使用 uv 管理 Python、虚拟环境和依赖。
- Python 固定为 3.12.15，版本记录在 `.python-version`。
- Windows 在 WSL Ubuntu 内执行命令；Mac 在终端执行相同的 uv 命令。
- 当前直接在 WSL / Mac 运行 Python，无需 Docker。

## 首次准备与运行

在 WSL 中进入项目目录：

```bash
cd /home/jacky/chaintrace
```

在 Mac 上进入实际克隆目录，然后同样执行：

```bash
uv sync --locked
uv run --locked python --version
uv run --locked chaintrace
```

首次同步时，uv 会按需下载指定 Python 并创建本机 `.venv`。
`uv run` 自动使用项目虚拟环境，不需要手动激活。
入口命令当前只输出环境信息，不访问网络或读取密钥。

## 管理依赖

```bash
uv add <包名>
uv add --dev <开发工具包名>
```

依赖变化后，将 `pyproject.toml` 与 `uv.lock` 一起提交。

## 在 Windows 与 Mac 之间同步

同步代码、README、`.python-version`、`pyproject.toml` 和 `uv.lock`。
换电脑后先拉取代码，再运行 `uv sync --locked`。
`.venv` 由每台电脑各自创建，不复制、不提交。
当前已初始化本地 Git 仓库，尚未添加远程地址或创建提交。

## 本地配置与数据

`.env`、私钥、日志和运行数据不提交 Git。
以后需要 RPC 配置时，提供不含密钥的 `.env.example`。
当前没有 RPC 配置，也没有添加区块链 SDK；在第一个查询实验中按需加入。
