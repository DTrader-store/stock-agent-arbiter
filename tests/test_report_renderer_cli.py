from __future__ import annotations

from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from tests.conftest import FakeLLM, FakeV3Client

from stock_agent_arbiter import cli
from stock_agent_arbiter.config import Settings
from stock_agent_arbiter.renderer import RichRenderer
from stock_agent_arbiter.report import MarkdownReportWriter, render_markdown
from stock_agent_arbiter.v3_adapter import MarketDataAdapter
from stock_agent_arbiter.workflow import StockArbiterWorkflow


def test_markdown_report_contains_core_sections(fake_llm, tmp_path) -> None:
    state = StockArbiterWorkflow(MarketDataAdapter(FakeV3Client()), fake_llm).run("600519")

    path = MarkdownReportWriter().write(state, tmp_path)
    text = path.read_text(encoding="utf-8")

    assert "## 数据状态" in text
    assert "## 买方证据" in text
    assert "## 卖方证据" in text
    assert "## 三轮辩论" in text
    assert "## 仲裁汇总" in text
    assert "本报告不构成交易建议" in text


def test_rich_renderer_handles_workflow_updates(fake_llm) -> None:
    console = Console(record=True, width=100)
    renderer = RichRenderer(console)
    workflow = StockArbiterWorkflow(MarketDataAdapter(FakeV3Client()), fake_llm)

    renderer.start("600519")
    for node, update, _state in workflow.stream("600519"):
        renderer.update(node, update)

    output = console.export_text()
    assert "Stock Agent Arbiter" in output
    assert "V3 数据快照" in output
    assert "仲裁汇总" in output


def test_cli_smoke_uses_fakes_without_real_v3_or_llm(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    settings = Settings(
        dtrader_base_url="https://v3.example",
        dtrader_auth="secret",
        openai_api_key="openai",
        openai_model="model",
        output_dir=tmp_path,
    )

    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "create_dtrader_client", lambda _settings: FakeV3Client())
    monkeypatch.setattr(cli, "create_chat_model", lambda _settings: FakeLLM())

    result = runner.invoke(cli.app, ["600519"])

    assert result.exit_code == 0, result.output
    reports = list(Path(tmp_path).glob("600519-*.md"))
    assert len(reports) == 1
    assert "仲裁汇总" in reports[0].read_text(encoding="utf-8")


def test_render_markdown_records_missing_data_while_debate_continues(fake_llm) -> None:
    state = StockArbiterWorkflow(MarketDataAdapter(FakeV3Client(empty="quote")), fake_llm).run("600519")

    text = render_markdown(state)

    assert "第 1 轮" in text
    assert "quote: empty data" in text
