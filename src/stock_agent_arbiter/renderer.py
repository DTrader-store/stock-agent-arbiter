from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .models import ArbiterState, ArbiterSummary, DebateTurn, EvidenceSnapshot, RoleEvidence


class RichRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def start(self, code: str) -> None:
        self.console.print(Panel(f"股票代码：{code}\n只读 V3 数据取证 + 三轮角色辩论", title="Stock Agent Arbiter", border_style="cyan"))

    def update(self, node: str, update: dict[str, Any]) -> None:
        if node == "collect_data" and "snapshot" in update:
            self._snapshot(update["snapshot"])
        elif node == "validate_data":
            self._validation(update)
        elif node == "buyer_evidence" and "buyer_evidence" in update:
            self._role_evidence("买方证据", update["buyer_evidence"], "green")
        elif node == "seller_evidence" and "seller_evidence" in update:
            self._role_evidence("卖方证据", update["seller_evidence"], "red")
        elif node == "debate" and "debate" in update:
            self._debate(update["debate"])
        elif node in {"arbiter", "abort"} and "summary" in update:
            self._summary(update["summary"])

    def report_written(self, path: Path) -> None:
        self.console.print(Panel(str(path), title="Markdown 报告已生成", border_style="blue"))

    def error(self, title: str, message: str) -> None:
        self.console.print(Panel(message, title=title, border_style="red"))

    def _snapshot(self, snapshot: EvidenceSnapshot) -> None:
        table = Table(title="V3 数据快照", show_header=True, header_style="bold cyan")
        table.add_column("来源")
        table.add_column("状态")
        table.add_column("说明")
        for name in snapshot.sources:
            if name in snapshot.missing:
                table.add_row(name, "[red]missing[/red]", snapshot.missing[name])
            else:
                table.add_row(name, "[green]ok[/green]", "")
        self.console.print(table)

    def _validation(self, update: dict[str, Any]) -> None:
        if update.get("aborted"):
            missing = update.get("missing_data", {})
            body = "\n".join(f"- {name}: {reason}" for name, reason in missing.items())
            self.console.print(Panel(body, title="全部 V3 数据缺失，已中止辩论", border_style="red"))
        elif update.get("missing_data"):
            missing = update.get("missing_data", {})
            body = "\n".join(f"- {name}: {reason}" for name, reason in missing.items())
            self.console.print(Panel(body, title="部分 V3 数据缺失，将使用可用数据继续", border_style="yellow"))
        else:
            self.console.print(Panel("必要 V3 数据已获取，开始买卖双方取证。", title="数据校验通过", border_style="green"))

    def _role_evidence(self, title: str, evidence: RoleEvidence, style: str) -> None:
        self.console.print(Panel(Markdown(evidence.content), title=title, border_style=style))

    def _debate(self, debate: list[DebateTurn]) -> None:
        for turn in debate:
            table = Table(title=f"第 {turn.round_number} 轮辩论", show_header=True, header_style="bold magenta")
            table.add_column("角色", width=10)
            table.add_column("观点")
            table.add_row("买方", turn.buyer_argument)
            table.add_row("卖方", turn.seller_argument)
            self.console.print(table)

    def _summary(self, summary: ArbiterSummary) -> None:
        table = Table(title="仲裁汇总：证据强弱", show_header=True, header_style="bold blue")
        table.add_column("部分", width=16)
        table.add_column("内容")
        table.add_row("买方最强证据", _join_items(summary.buyer_strongest_evidence))
        table.add_row("卖方最强证据", _join_items(summary.seller_strongest_evidence))
        table.add_row("双方争议点", _join_items(summary.disputed_points))
        table.add_row("证据缺口", _join_items(summary.evidence_gaps))
        table.add_row("保守总结", summary.conservative_summary or "未生成。")
        table.add_row("声明", summary.disclaimer or "本报告不构成交易建议。")
        self.console.print(table)


def _join_items(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "未生成。"
