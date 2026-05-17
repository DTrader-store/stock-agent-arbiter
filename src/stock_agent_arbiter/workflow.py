from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from typing import Any, Protocol, cast

from langgraph.graph import END, StateGraph

from .models import ArbiterState, ArbiterSummary, DebateTurn, EvidenceSnapshot, RoleEvidence, compact_sources
from .prompts import ABORT_SUMMARY, ARBITER_SYSTEM, BUYER_EVIDENCE_SYSTEM, DEBATE_SYSTEM, SELLER_EVIDENCE_SYSTEM
from .v3_adapter import MarketDataAdapter, validate_stock_code


class ChatModel(Protocol):
    def invoke(self, messages: Sequence[tuple[str, str]]) -> Any: ...


class StockArbiterWorkflow:
    def __init__(self, market_data: MarketDataAdapter, llm: ChatModel) -> None:
        self._market_data = market_data
        self._llm = llm
        self._graph = self._build_graph()

    def run(self, code: str) -> ArbiterState:
        initial: ArbiterState = {"code": validate_stock_code(code)}
        return cast(ArbiterState, self._graph.invoke(initial))

    def stream(self, code: str) -> Iterator[tuple[str, dict[str, Any], ArbiterState]]:
        state: ArbiterState = {"code": validate_stock_code(code)}
        for event in self._graph.stream(state):
            for node, update in event.items():
                if isinstance(update, dict):
                    state.update(cast(ArbiterState, update))
                    yield node, update, state

    def _build_graph(self):
        graph = StateGraph(ArbiterState)
        graph.add_node("collect_data", self._collect_data)
        graph.add_node("validate_data", self._validate_data)
        graph.add_node("buyer_evidence", self._buyer_evidence)
        graph.add_node("seller_evidence", self._seller_evidence)
        graph.add_node("debate", self._debate)
        graph.add_node("arbiter", self._arbiter)
        graph.add_node("abort", self._abort)
        graph.set_entry_point("collect_data")
        graph.add_edge("collect_data", "validate_data")
        graph.add_conditional_edges("validate_data", self._route_after_validation, {"abort": "abort", "continue": "buyer_evidence"})
        graph.add_edge("buyer_evidence", "seller_evidence")
        graph.add_edge("seller_evidence", "debate")
        graph.add_edge("debate", "arbiter")
        graph.add_edge("arbiter", END)
        graph.add_edge("abort", END)
        return graph.compile()

    def _collect_data(self, state: ArbiterState) -> ArbiterState:
        snapshot = self._market_data.fetch_basic_evidence(state["code"])
        return {"snapshot": snapshot}

    def _validate_data(self, state: ArbiterState) -> ArbiterState:
        snapshot = state["snapshot"]
        missing = dict(snapshot.missing)
        available_sources = [name for name in snapshot.sources if name not in missing]
        return {"missing_data": missing, "aborted": not available_sources}

    def _route_after_validation(self, state: ArbiterState) -> str:
        return "abort" if state.get("aborted") else "continue"

    def _buyer_evidence(self, state: ArbiterState) -> ArbiterState:
        snapshot = state["snapshot"]
        content = self._invoke_text(
            BUYER_EVIDENCE_SYSTEM,
            f"股票代码：{snapshot.code}\n共享 V3 数据快照：\n{_snapshot_for_prompt(snapshot)}",
        )
        return {"buyer_evidence": RoleEvidence(role="buyer", stance="buy-side evidence", content=content)}

    def _seller_evidence(self, state: ArbiterState) -> ArbiterState:
        snapshot = state["snapshot"]
        content = self._invoke_text(
            SELLER_EVIDENCE_SYSTEM,
            (
                f"股票代码：{snapshot.code}\n共享 V3 数据快照：\n{_snapshot_for_prompt(snapshot)}\n\n"
                f"买方证据：\n{state['buyer_evidence'].content}"
            ),
        )
        return {"seller_evidence": RoleEvidence(role="seller", stance="sell-side evidence", content=content)}

    def _debate(self, state: ArbiterState) -> ArbiterState:
        debate: list[DebateTurn] = []
        for round_number in range(1, 4):
            shared_context = _debate_context(state, debate)
            buyer_argument = self._invoke_text(
                DEBATE_SYSTEM,
                f"第 {round_number} 轮。你是买方。请回应卖方并强化买方证据。\n\n{shared_context}",
            )
            seller_argument = self._invoke_text(
                DEBATE_SYSTEM,
                (
                    f"第 {round_number} 轮。你是卖方。请回应买方刚才观点并强化卖方证据。\n\n"
                    f"{shared_context}\n\n买方本轮观点：\n{buyer_argument}"
                ),
            )
            debate.append(DebateTurn(round_number=round_number, buyer_argument=buyer_argument, seller_argument=seller_argument))
        return {"debate": debate}

    def _arbiter(self, state: ArbiterState) -> ArbiterState:
        content = self._invoke_text(
            ARBITER_SYSTEM,
            (
                f"股票代码：{state['code']}\n"
                f"共享 V3 数据快照：\n{_snapshot_for_prompt(state['snapshot'])}\n\n"
                f"买方证据：\n{state['buyer_evidence'].content}\n\n"
                f"卖方证据：\n{state['seller_evidence'].content}\n\n"
                f"三轮辩论：\n{_format_debate(state['debate'])}"
            ),
        )
        summary = _parse_arbiter_summary(content)
        return {"summary": _summary_with_missing_data_gaps(summary, state.get("missing_data", {}))}

    def _abort(self, state: ArbiterState) -> ArbiterState:
        missing = state.get("missing_data", {})
        summary = ArbiterSummary(
            evidence_gaps=[f"{name}: {reason}" for name, reason in missing.items()],
            conservative_summary=ABORT_SUMMARY,
            disclaimer="本报告不构成交易建议。",
        )
        return {"summary": summary, "debate": []}

    def _invoke_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self._llm.invoke([("system", system_prompt), ("user", user_prompt)])
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "\n".join(str(item) for item in content).strip()
        return str(content).strip()


def _snapshot_for_prompt(snapshot: EvidenceSnapshot) -> str:
    available_sources = {name: value for name, value in snapshot.sources.items() if name not in snapshot.missing}
    return compact_sources(available_sources)


def _debate_context(state: ArbiterState, debate: list[DebateTurn]) -> str:
    return (
        f"股票代码：{state['code']}\n"
        f"买方证据：\n{state['buyer_evidence'].content}\n\n"
        f"卖方证据：\n{state['seller_evidence'].content}\n\n"
        f"已完成辩论：\n{_format_debate(debate) if debate else '暂无'}"
    )


def _format_debate(debate: list[DebateTurn]) -> str:
    parts: list[str] = []
    for turn in debate:
        parts.append(
            f"第 {turn.round_number} 轮\n"
            f"买方：{turn.buyer_argument}\n"
            f"卖方：{turn.seller_argument}"
        )
    return "\n\n".join(parts)


def _parse_arbiter_summary(content: str) -> ArbiterSummary:
    candidate = _extract_json(content)
    try:
        payload = json.loads(candidate)
        return ArbiterSummary.model_validate(payload)
    except Exception:
        return ArbiterSummary(
            evidence_gaps=["仲裁模型未返回可解析的结构化 JSON。"],
            conservative_summary=content,
            disclaimer="本报告不构成交易建议。",
        )


def _extract_json(content: str) -> str:
    stripped = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _summary_with_missing_data_gaps(summary: ArbiterSummary, missing_data: dict[str, str]) -> ArbiterSummary:
    if not missing_data:
        return summary
    gaps = list(summary.evidence_gaps)
    for name, reason in missing_data.items():
        gap = f"{name}: {reason}"
        if gap not in gaps:
            gaps.append(gap)
    return summary.model_copy(update={"evidence_gaps": gaps})
