# Stock Agent Arbiter

Python + LangGraph CLI for a read-only stock evidence debate:

1. Fetch a shared DTrader V3 market-data snapshot for one stock code.
2. Ask buyer and seller roles to extract opposing evidence from that same snapshot.
3. Run three debate rounds.
4. Produce an arbiter evidence-strength summary.
5. Render the process in Rich and save a Markdown report.

This tool is for research assistance and process review only. It does not place orders and does not provide investment advice.

## Setup

```sh
uv sync
```

Configure environment variables:

```sh
export DTRADER_BASE_URL="https://your-endpoint"
export DTRADER_AUTH="your key"
export OPENAI_API_KEY="your key"
export OPENAI_MODEL="your model"
# Optional for OpenAI-compatible providers:
export OPENAI_BASE_URL="https://your-compatible-endpoint/v1"
# Optional report directory:
export STOCK_AGENT_OUTPUT_DIR="reports"
```

Run:

```sh
uv run stock-agent-arbiter 600519
```

## Scope

- Input: one stock code.
- V3 access: read-only market data through `dtrader-v3-sdk`.
- Output: Rich terminal panels plus `reports/{code}-{timestamp}.md`.
- Not supported in v1: batch input, free-text stock questions, HTTP API, Web UI, JSON export, account access, position access, or trading mutations.
