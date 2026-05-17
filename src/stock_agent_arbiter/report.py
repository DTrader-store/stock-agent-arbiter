from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import ArbiterState, ArbiterSummary, DebateTurn, EvidenceSnapshot, compact_json


class MarkdownReportWriter:
    def write(self, state: ArbiterState, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
        path = output_dir / f"{state['code']}-{timestamp}.md"
        path.write_text(render_markdown(state), encoding="utf-8")
        return path


def render_markdown(state: ArbiterState) -> str:
    snapshot = state.get("snapshot")
    summary = state.get("summary", ArbiterSummary())
    lines = [
        f"# Stock Agent Arbiter Report: {state.get('code', '')}",
        "",
        "> 本报告不构成交易建议。",
        "",
        "## 数据状态",
        "",
    ]
    if snapshot:
        lines.extend(_snapshot_section(snapshot))
    else:
        lines.append("- 未获取到 V3 数据快照。")
    lines.extend(
        [
            "",
            "## 买方证据",
            "",
            state["buyer_evidence"].content if "buyer_evidence" in state else "未生成。",
            "",
            "## 卖方证据",
            "",
            state["seller_evidence"].content if "seller_evidence" in state else "未生成。",
            "",
            "## 三轮辩论",
            "",
        ]
    )
    debate = state.get("debate", [])
    lines.extend(_debate_section(debate))
    lines.extend(
        [
            "",
            "## 仲裁汇总",
            "",
            "### 买方最强证据",
            "",
            _bullet_list(summary.buyer_strongest_evidence),
            "",
            "### 卖方最强证据",
            "",
            _bullet_list(summary.seller_strongest_evidence),
            "",
            "### 双方争议点",
            "",
            _bullet_list(summary.disputed_points),
            "",
            "### 证据缺口",
            "",
            _bullet_list(summary.evidence_gaps),
            "",
            "### 保守总结",
            "",
            summary.conservative_summary or "未生成。",
            "",
            f"> {summary.disclaimer or '本报告不构成交易建议。'}",
            "",
        ]
    )
    return "\n".join(lines)


def _snapshot_section(snapshot: EvidenceSnapshot) -> list[str]:
    lines = [f"- 股票代码：`{snapshot.code}`", f"- 数据完整：`{snapshot.is_complete}`", "- 来源："]
    for name in snapshot.sources:
        status = "missing" if name in snapshot.missing else "ok"
        lines.append(f"  - `{name}`: {status}")
    if snapshot.missing:
        lines.append("- 缺失项：")
        for name, reason in snapshot.missing.items():
            lines.append(f"  - `{name}`: {reason}")
    lines.extend(["", "### 原始快照摘录", "", "```json", compact_json(snapshot.sources, max_chars=20_000), "```"])
    return lines


def _debate_section(debate: list[DebateTurn]) -> list[str]:
    if not debate:
        return ["未生成辩论。"]
    lines: list[str] = []
    for turn in debate:
        lines.extend(
            [
                f"### 第 {turn.round_number} 轮",
                "",
                f"**买方：** {turn.buyer_argument}",
                "",
                f"**卖方：** {turn.seller_argument}",
                "",
            ]
        )
    return lines


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- 未生成。"
    return "\n".join(f"- {item}" for item in items)
