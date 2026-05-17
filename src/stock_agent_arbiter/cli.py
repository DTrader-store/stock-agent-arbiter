from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .config import ConfigurationError, Settings, create_chat_model, create_dtrader_client
from .renderer import RichRenderer
from .report import MarkdownReportWriter
from .v3_adapter import MarketDataAdapter, validate_stock_code
from .workflow import StockArbiterWorkflow

app = typer.Typer(add_completion=False, invoke_without_command=True, no_args_is_help=True)


@app.callback()
def main(
    ctx: typer.Context,
    code: Annotated[str | None, typer.Argument(help="Single stock code, for example 600519.")] = None,
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if code is None:
        raise typer.BadParameter("stock code is required")
    run_cli(code)


def run_cli(code: str) -> Path:
    console = Console()
    renderer = RichRenderer(console)
    try:
        normalized_code = validate_stock_code(code)
        settings = Settings.from_env()
        v3_client = create_dtrader_client(settings)
        llm = create_chat_model(settings)
        workflow = StockArbiterWorkflow(MarketDataAdapter(v3_client), llm)
        writer = MarkdownReportWriter()

        renderer.start(normalized_code)
        final_state = None
        for node, update, state in workflow.stream(normalized_code):
            renderer.update(node, update)
            final_state = state
        if final_state is None:
            final_state = workflow.run(normalized_code)
        report_path = writer.write(final_state, settings.output_dir)
        renderer.report_written(report_path)
        return report_path
    except ValueError as exc:
        renderer.error("输入错误", str(exc))
        raise typer.Exit(2) from exc
    except ConfigurationError as exc:
        renderer.error("配置错误", str(exc))
        raise typer.Exit(2) from exc
    except Exception as exc:
        renderer.error("运行失败", str(exc))
        raise typer.Exit(1) from exc
