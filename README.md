# Stock Agent Arbiter

一个基于 Python、DTrader V3 和 LangGraph 的股票 AI Agent 命令行工具，用于围绕同一份只读行情数据生成买卖双方证据辩论和仲裁汇总。

流程：

1. 为单只股票获取一份共享的 DTrader V3 市场数据快照。
2. 让买方和卖方角色基于同一份快照提取相反方向的证据。
3. 执行三轮买卖双方辩论。
4. 生成仲裁者视角的证据强弱汇总。
5. 使用 Rich 在终端展示完整过程，并保存 Markdown 报告。

本工具仅用于研究辅助和过程复盘，不会下单，也不构成投资建议。

<img width="1005" height="838" alt="image" src="https://github.com/user-attachments/assets/eb478552-19d2-4bea-a6ee-45775dfa3bc1" />
<img width="1011" height="848" alt="image" src="https://github.com/user-attachments/assets/64d21804-23f2-4902-8f9f-2a338331d666" />

## 安装

```sh
uv sync
```

## 配置

配置环境变量：

```sh
export DTRADER_BASE_URL="https://your-endpoint"
export DTRADER_AUTH="your key"
export OPENAI_API_KEY="your key"
export OPENAI_MODEL="your model"
# OpenAI 兼容服务可选：
export OPENAI_BASE_URL="https://your-compatible-endpoint/v1"
# 报告目录可选：
export STOCK_AGENT_OUTPUT_DIR="reports"
```

也可以参考 `.env.example` 创建本地 `.env` 文件。

## 运行

```sh
uv run stock-agent-arbiter 600519
```

运行后会在终端展示：

- V3 数据快照状态
- 买方证据
- 卖方证据
- 三轮辩论
- 仲裁汇总
- Markdown 报告路径

报告默认保存到：

```text
reports/{code}-{timestamp}.md
```

## 范围

- 输入：单个股票代码。
- V3 访问：通过 `dtrader-v3-sdk` 读取只读市场数据。
- 输出：Rich 终端面板和 `reports/{code}-{timestamp}.md` Markdown 报告。
- 部分数据源不可用时：继续使用已有数据生成辩论，并把不可用来源记录为证据缺口。
- 所有数据源都不可用时：中止辩论，只记录数据状态。

## 当前不支持

- 批量股票输入
- 自由文本股票问答
- HTTP API
- Web UI
- JSON 导出
- 账户访问
- 持仓访问
- 交易相关写操作
