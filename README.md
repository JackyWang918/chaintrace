# ChainTrace（链迹）

使用 Python 学习 EVM 链上数据，逐步构建 ERC-20 地址转账监控系统。
M1、M2 已按学习计划完成。现有主网 USDC 余额、代币信息与授权额度只读查询；M3 已实现单笔回执、最多两个区块的 Transfer 日志读取、本地 SQLite 幂等入库及只读 RPC 的有限超时重试。尚无大范围批量采集、HTTP 限流重试或持续监控；没有代币转账或授权写入。详细证据与限制见 `docs/progress.md`。

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

## M3：读取一笔交易的 USDC Transfer 日志

```bash
uv run --locked chaintrace token-transfers 0x1900e0a964f47694109351754e87cab78fe05b3fe0e511dc7fc70a173f88f5a1
```

只读实验：读取交易和回执，核对哈希与区块，按主网 USDC 合约地址和 Transfer 事件标识筛选日志。交易 From 是请求发起者，交易 To 是被调用地址；日志 Token from/to 才是该条代币转账的收发方，两组地址不能混用。topics[0] 是事件标识，topics[1:3] 是补零后的收发地址，data 是 32 字节原始金额；程序在回执区块查询 decimals，以整数精确换算。

输出区块哈希、区块内 logIndex、原始 topics/data 与浏览器链接；核对交易 From/To、日志所属合约、代币收发地址和数量。公共 RPC 可能不提供某些历史回执，返回 null 时状态未知，不判失败；无匹配日志不等于一条金额为零的转账，数据格式错误也不当成零。未检查最终确定性，不推断交易完整业务目的，不入库或批量采集。样例已有 AI 和用户 RPC 查询证据，用户反馈浏览器字段全部一致，正常样例交叉核验已完成；筛选与解码关键代码已展示，用户已正确回答相关预测，零金额离线对照的用户运行尚无反馈。

M3 无日志与零金额日志的离线对照：

```bash
uv run --locked python examples/transfer_log_cases.py
```

脚本以模拟回执调用现有解析代码，不读取本地 RPC 配置、不访问网络。两个成功回执分别包含空日志列表和一条有效零金额 Transfer；前者报告没有匹配日志，后者显示 1 条日志及 0 USDC。脚本带结果断言，用于核验缺记录与数值零的区别，不代表真实链上实验。

## M3：按一个或两个区块查询 USDC 日志

```bash
uv run --locked chaintrace token-logs 26224712
```

参数为非负十进制区块号；省略结束区块时只查起始区块，也可以指定包含两端的范围。当前学习实验最多查两个区块，反向范围或超过两个区块会在发出请求前报错，这是教学范围限制，不是 RPC 协议限制。本实验先确认主网并读取范围内各区块头，再通过 eth_getLogs 按 fromBlock/toBlock、address=USDC 合约、topics[0]=Transfer 标识查询，复用已有 ABI 解码。检查每条日志的区块号、区块哈希、removed 标记和事件条件，按区块号及区块内 logIndex 排序。同一交易的多条日志分别展示；不同区块的相同 logIndex 合法，同一区块重复 logIndex 报错。日志数、匹配交易数及每个区块的日志数分别统计。

两个相邻区块的最小范围实验：

```bash
uv run --locked chaintrace token-logs 26224712 26224713
```

AI 实测分别为 64、67 条日志，共 131 条、80 笔匹配交易；与两个单区块查询的有序日志记录逐条对照一致。用户已运行并提供一致的统计和两个区块元数据。这只是同一 RPC 的跨请求核验，不是独立节点或浏览器全量核验。下一批不重叠范围从前一批结束区块 +1 开始；当前不自动推进采集进度。

本命令只显示原始整数金额，不调用 decimals、不猜小数位数。实测读取该历史区块 decimals 曾收到 HTTP 403；单笔 token-transfers 命令仍保留其精确金额换算。日志时间取自区块时间；Gas 与执行状态不作为每条日志独立字段展示。

单区块 AI 样例：26224712 返回 64 条匹配日志，来自 41 笔不同交易；前两条的交易哈希相同但 logIndex 分别为 0 和 4。用户已运行并提供一致的统计与前两条日志输出，该块全量完整性及前两条浏览器独立核验尚未完成。用户之前核验的交易 `0x1900e0a964f47694109351754e87cab78fe05b3fe0e511dc7fc70a173f88f5a1` 也在 AI 单区块结果中，logIndex=3015、原始金额=499921670。空列表与查询失败分开处理；本查询命令不写数据库，入库使用下方独立命令。已加入下述有限超时重试，尚无大范围批量采集、HTTP 限流重试、检查点或重组恢复，不将一两个区块读取成功视为可靠采集验收通过。

M3 查询失败与空列表的离线对照：

```bash
uv run --locked python examples/block_query_failure.py
```

脚本用模拟 HTTP 响应/HTTPError 调用真实命令入口和 RPC 错误处理，不访问网络，不写数据库或采集进度。空列表成功时模拟命令退出码为 0、日志数为 0；HTTP 403 时模拟命令退出码为 1，报告查询失败，不生成空结果。脚本捕获预期退出并断言，因此脚本整体成功结束不代表模拟请求均成功。当前尚无检查点或自动补数功能。

## M3：最小 SQLite 入库与重复采集

在项目目录连续运行同一条命令两次：

```bash
uv run --locked chaintrace collect-token-logs 26224712 26224713
```

默认写入项目 `data/chaintrace.sqlite3`，可用 `--db data/other.sqlite3` 指定其他本地文件；数据目录与 SQLite 文件均被 Git 忽略。只使用 Python 标准库 sqlite3，无新增依赖，不需要数据库服务。区块范围仍最多两个，省略结束区块时采集单块。查询命令 token-logs 保持只读；本命令写本地数据库，不发起链上交易。

`transfers` 保存链 ID、代币合约、区块号与哈希、交易哈希、logIndex、代币发送方和接收方、原始金额、区块 Unix 时间。主键是 `(chain_id, block_hash, log_index)`；区块号仍存储，但不必再加入主键。原始金额用规范十进制 TEXT 保存，读取后可转为 Python int；不转浮点，也不塞入 SQLite 的有符号整数列。

先取得并验证整批 RPC 数据，再打开数据库，用一个事务提交。重复标识且全部字段一致时跳过；同一标识内容冲突则报错并回滚本批新增行，不能用 INSERT OR IGNORE 掩盖内容差异。写入失败同样回滚。已有成功批次保留；当前没有采集检查点，不将空列表或已有记录当成区块采集状态。

空数据库的预期结果：第一次 `Inserted: 131`、`Already stored (identical): 0`、总数 131；第二次新增 0、已存在 131、总数仍 131。总数是整个数据库的记录数；若该文件已有其他区块，可能大于 131。AI 已在临时数据库完成两次主网运行和数据库字段抽样核对；用户也已在默认项目库连续两次运行，所有计数符合预期。正常幂等及下方模拟内容冲突回滚的用户学习实验均已完成。

离线内容冲突与整批回滚对照：

```bash
uv run --locked python examples/storage_conflict.py
```

脚本只用模拟日志和临时数据库，保留 131 条初始记录后尝试写入 3 条新记录，再制造相同主键的原始金额 100→200 冲突。预期报告冲突，总数仍为 131、新行残留 0、旧金额仍为 100；脚本逐字段断言初始记录全部不变。AI 和用户均已运行，结果符合预期。不会打开默认项目库，不访问 RPC，临时库自动清理。

这是保存特定区块哈希下日志的最小实验，尚不判断哪条分支属于当前主链。不同区块哈希的观察记录可并存；链重组的识别与处理留到 M5，不据此宣称已有可靠余额统计或持续监控。SQLite 事务用法参考 [Python sqlite3 文档](https://docs.python.org/3.12/library/sqlite3.html)。

## M3：只读 RPC 的有限超时重试

```bash
uv run --locked python examples/rpc_timeout_retry.py
```

当前仅对明确的只读方法白名单处理传输超时：包括链 ID、高度、余额、交易/回执、区块、日志及 eth_call。每个 RPC 请求最多尝试 3 次（含首次），前两次超时分别等待 1、2 秒；第三次仍超时则报错退出。成功立即返回相同方法与参数的查询结果，不额外重试成功空列表。每次传输超时设置仍为 15 秒；尝试次数是针对单个 RPC，不是整批所有 RPC 的总次数。重试提示写入 stderr，不打印 RPC URL 或密钥。

识别直接 TimeoutError 或 URLError 包裹的 TimeoutError。其他连接错误、HTTP 状态错误（包括 403、429、503）、JSON/JSON-RPC 错误和数据校验错误均直接失败；本小步尚未实现 429/Retry-After。入库内容冲突也不重试。白名单外方法只尝试一次，此策略不自动延伸到未来签名广播。403 表示拒绝访问，不能当作零条数据；429 表示限流，后续再单独处理等待规则。

离线脚本替换 HTTP 传输和 sleep，使用模拟日志和临时数据库，不访问网络、不真实等待、不打开项目默认库。三组断言：前两次超时后成功时 eth_getLogs 请求 3 次、等待 2 次、入库 1 批且库中 131 条；三次超时时请求 3 次、等待 2 次、退出码 1、入库 0 批且库文件不存在；403 时请求 1 次、等待 0 次、退出码 1、入库 0 批。AI 和用户均已运行，三组结果符合预期。各模拟命令的退出码由脚本捕获，脚本整体成功结束表示断言通过。

RPC 整批取得并验证成功后才打开数据库，因此查询重试发生在数据库事务外；不在 SQLite 写事务内等待网络。还没有检查点、自动补数或持续运行，也未声称观察过真实节点超时恢复。

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
