# 学习进度

最后更新：2026-10-15（Asia/Shanghai）。

## 当前状态

- 当前里程碑：M1，读懂一笔交易。
- 已完成：M1-0，Python 环境准备。
- 下一步：M1-1，先理解 Python → RPC 节点 → 链上数据，再查询链 ID 和区块高度。
- M1 链上查询尚未开始；M1 整体验收尚未通过。
- M2–M6 均未开始。

## 已有证据

- 项目位于 WSL Ubuntu `/home/jacky/chaintrace`；Windows 对应 `\\wsl.localhost\Ubuntu\home\jacky\chaintrace`。
- uv 0.13.0；项目 Python 固定为 3.12.15；`.venv` 已创建。
- `uv sync --locked` 执行成功。
- `uv run --locked chaintrace` 输出 Python 3.12.15、Linux x86_64、Virtual environment: True。
- Git 远程：`https://github.com/JackyWang918/chaintrace.git`，分支 `main`。
- 环境初始化提交：`c728a8f`，已推送到 `origin/main`。
- 本次初始化推送使用 Windows Git 凭据完成；WSL 自身当时未配置 GitHub 凭据，后续以实际状态为准。
- Mac 尚未验证；在 Mac 拉取后执行 `uv sync --locked` 和环境入口命令验收。

## 尚未完成

- 未选择或配置 RPC 服务，没有 `.env` 或 `.env.example`。
- 未安装区块链查询 SDK；当前项目无运行时第三方依赖。
- 未查询链 ID、区块高度、余额、交易或回执。
- 尚无链上数据核验记录或用户对 M1 概念的验收解释。

## 新窗口问“M1 计划如何开始”时

从 **M1-1** 接续，不重复搭建已经验收过的 WSL 环境；新机器可先运行环境验收。
先标明当前位置、本次问题和完成证据，解释节点与 RPC、请求和返回的数据流。
然后请用户预测：查询公开区块高度是否需要钱包、私钥或支付 Gas？
等待用户回答后再推进最小查询；如果用户明确要求直接实现，则按新指示执行。
不要一次完成余额、交易、入库或监控功能。

## 后续记录要求

每次学习后更新：完成步骤、运行命令、核验结果、用户自己的解释、未解决问题、下一小步。
公开样例可记录网络、区块高度、地址、交易哈希和查询时间，便于另一台电脑复现。
记录中不得包含 RPC 密钥或私钥；不要把代码运行成功等同于概念已经掌握。
