# ChainTrace（链迹）

使用 Python 学习 EVM 链上数据，逐步构建 ERC-20 地址转账监控系统。
M1、M2 已按学习计划完成。现有主网 USDC 余额、代币信息与授权额度只读查询；M3 历史转账采集尚未开始，尚未实现代币转账或授权写入。详细证据与限制见 `docs/progress.md`。

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
仓库：https://github.com/JackyWang918/chaintrace.git，默认分支为 `main`。

## 本地配置与数据

`.env`、私钥、日志和运行数据不提交 Git。
以后需要 RPC 配置时，提供不含密钥的 `.env.example`。
M1-1 使用 Python 标准库调用 JSON-RPC，使用 python-dotenv 加载本地配置，暂不需要区块链 SDK。

## M1-1：第一次只读查询

在项目根目录运行（Windows 使用 WSL 终端）：

```bash
cp -n .env.example .env
uv run --locked chaintrace network
```

示例使用 PublicNode 的以太坊主网公共 RPC，不需要钱包或私钥。
程序先调用 `eth_chainId`，确认链 ID 为 `1`，再调用 `eth_blockNumber`。
RPC 原始整数以 `0x` 开头，程序用 `int(raw, 16)` 转成十进制。
输出包含查询时间与对应 Etherscan 区块链接；高度随时间变化，旧结果不代表当前最新高度。
打开链接核对区块是否存在，再查看浏览器最新高度；不同查询时间或节点同步差异可能造成高度差。
公共 RPC 可能超时或限流；失败时程序报错并以非零状态退出，不将错误当成区块高度。
本地 `.env` 不提交；已有 shell 环境变量优先于 `.env`。

制造一次连接失败（仅对这条命令覆盖配置，不修改 `.env`）：

```bash
NO_PROXY=127.0.0.1 no_proxy=127.0.0.1 ETH_RPC_URL=http://127.0.0.1:1 uv run --locked chaintrace network
```

预期显示连接失败并退出；该实验假设本机端口 1 没有服务。
这表示本次未能查询节点，不能据此判断区块链停止出块。

## M1-2：地址余额

M1-2 查询一个公开示例地址的 ETH 余额：

```bash
uv run --locked chaintrace balance 0x000000000000000000000000000000000000dEaD
```

该示例地址用于学习公开余额查询，不需要钱包或私钥。程序先确认链 ID 为 `1`，取得一个区块号，再调用 `eth_getBalance` 查询该区块的余额，输出原始 wei 和精确的 ETH 换算。`1 ETH = 10^18 wei`；换算使用整数拆分，没有浮点数。输出中的 Etherscan 地址页可辅助核对，但它通常显示当前余额；若查询时刻不同，不应直接要求金额完全相同。请先核对网络和地址，再比较区块或时间。

## M1-3：交易与回执

查询一笔公开、已执行的简单 ETH 转账（不会发起交易）：

```bash
uv run --locked chaintrace transaction 0x7e19e6872e065ee699f378b24da8e3f5dcb3e0bc15135905fb85748c81ff332f
```

程序分别调用 `eth_getTransactionByHash` 与 `eth_getTransactionReceipt`，输出请求的发送方、接收方、金额、Nonce、Gas 上限，以及回执中的区块、执行状态、实际 Gas 消耗与实际单价。金额和手续费使用整数计算。

本实验中 `status=1` 表示执行成功，`status=0` 表示执行失败；查不到交易或回执表示当前节点未提供对应结果，不等于执行失败。已查到回执时还会核对交易与回执的交易哈希、区块号和区块哈希是否一致。

执行手续费（wei）为 `gasUsed × effectiveGasPrice`，不是 Gas 上限乘价格；交易的 `value` 是请求金额，不能仅凭这个字段断言转账成功。这里解释简单主网 ETH 转账的执行费，不包含 blob 等其他交易类型的额外费用；未检查最终确定性。

打开输出的 Etherscan 链接，核对 From、To、Value、Block、Status、Transaction Fee。Nonce 是发送账户的交易序号，用于交易排序并防止同一笔已用序号的交易重复执行；本实验只读取，不构造或签名。

验证状态分支和费用计算：

```bash
uv run --locked python -m unittest discover -s tests -v
```

## M2：第一次代币余额查询

```bash
uv run --locked chaintrace token-balance 0x000000000000000000000000000000000000dEaD
```

目前只查询主网 USDC，合约按 [Circle 官方地址](https://developers.circle.com/stablecoins/usdc-contract-addresses) 固定为 `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`。资产身份是网络加合约地址；命令参数为持有者地址，不是代币合约地址。

程序通过 `eth_call` 读取同一区块的 `decimals()` 和 `balanceOf(address)`，输出原始代币整数与精确换算结果。显示数量为 `原始整数 / 10^decimals`；该整数不是 ETH 的 wei，不能默认除以 `10^18`。不发送交易，不需要私钥或支付链上 Gas。空返回和调用错误会报错，不视为余额零；decimals 缺失时不猜测默认值。

此命令中的 USDC 名称是按官方合约配置的标签；余额查询本身不调用 `name()` 或 `symbol()`。输出的 token 链接指定合约与持有者，核对时先确认两种地址；浏览器当前余额可能与指定区块的余额不同。此查询不会验证持有者的 ETH 余额。

## M2：代币信息

```bash
cp -n .env.example .env
uv run --locked chaintrace token-info
```

程序调用 `eth_chainId` 确认主网链 ID 为 1，随后在同一区块以 `eth_call` 读取上述合约的 `name()`、`symbol()` 和 `decimals()`。名称与简称是显示信息；识别此资产要同时看链 ID 和合约地址。`decimals` 用于将原始整数精确显示为代币数量，例如 `1234567`、`decimals=6` 显示为 `1.234567`。本命令只读，不需要私钥或链上 Gas。若元数据未按预期返回，程序报错，不猜测名称、简称或小数位数。区块浏览器可核对合约地址、简称和小数位数；其页面标题可能不等于合约 `name()` 的原始返回，页面也未必显式标出数字链 ID。未找到的字段应记为未核对，不强行视为一致；浏览器页面与命令指定的区块也可能不同。

## 学习衔接

M2 授权额度只读查询：

```bash
uv run --locked chaintrace token-allowance 0x000000000000000000000000000000000000dEaD 0x0000000000000000000000000000000000000001
```

第一个地址是代币持有者 `owner`，第二个是被授权者 `spender`。命令在同一区块读取主网 USDC 的 `decimals()` 与 `allowance(owner, spender)`，显示剩余额度，不执行 `approve` 或转账，也不会改变任何人的余额。示例地址对的结果可能随区块变化；查询到 0 只表示该区块的剩余额度为 0，不代表合约函数不存在。若假设 A 原有 10 USDC、B 原有 0 USDC，A 成功执行 `approve(B, 3 USDC)` 且尚无后续使用，则 A 仍为 10、B 仍为 0、`allowance(A,B)` 为 3；真实示例查询不能证明这件假设中的授权发生过。

M2 离线 ABI 返回值对照实验：

```bash
uv run --locked python examples/abi_returns.py
```

此脚本使用模拟 RPC 返回值，不访问网络。32 字节全零可解码为整数 0，空数据 `0x` 会被拒绝；用于说明不能把未取得有效数据当成余额零。

比较 `transfer` 与 `transferFrom` 的离线状态模型：

```bash
uv run --locked python examples/transfer_paths.py
```

脚本分别从 A=10、B=0、C=0、`allowance(A,B)=3 USDC` 开始，演示 A 直接转 2、B 用授权代 A 转 2，以及两笔连续执行。金额以 6 位小数的原始整数表示；额外演示额度不足时拒绝并保持状态。此模型不访问链、不签名或发送真实交易，不能证明真实 USDC 合约在所有条件下都按此执行。

- [整体学习计划](docs/learning-plan.md)：目标、M1–M6 路线、验收与教学方式。
- [当前进度](docs/progress.md)：已完成证据、尚未完成事项与下一小步。
- [AI 协作约定](AGENTS.md)：新对话先读取上述文件。

换电脑后先拉取最新代码，在项目目录开启新对话即可接续；若对话未加载此仓库，请先提供仓库位置或这些文件。
