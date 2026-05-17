from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest


class FakeV3Client:
    def __init__(self, *, empty: str | set[str] | None = None) -> None:
        self.empty = {empty} if isinstance(empty, str) else empty or set()
        self.calls: list[str] = []

    def _response(self, name: str, data: Any | None = None) -> dict[str, Any]:
        self.calls.append(name)
        if name in self.empty:
            return {"code": 0, "data": None}
        return {"code": 0, "data": data if data is not None else {"source": name, "value": 1}}

    def quote(self, code: str) -> dict[str, Any]:
        return self._response("quote", {"code": code, "price": 10.5, "changeRate": 1.2})

    def kline(self, code: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._response("kline", [{"close": 10.5, "volume": 1000, "query": query}])

    def details(self, code: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._response("details", [{"amount": 5000}])

    def trends(self, code: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._response("trends", [{"time": "10:00", "price": 10.4}])

    def finance(self, code: str) -> dict[str, Any]:
        return self._response("finance", {"pe": 12.3})

    def ranking_stocks(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._response("ranking_stocks", {"total": 1, "list": [{"code": "600519", "rank": 1}]})

    def ranking_boards(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._response("ranking_boards", {"total": 1, "list": [{"code": "BK0001", "name": "board"}]})


@dataclass
class FakeMessage:
    content: str


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[tuple[str, str]]] = []

    def invoke(self, messages: list[tuple[str, str]]) -> FakeMessage:
        self.calls.append(messages)
        system = messages[0][1]
        user = messages[1][1]
        if "严格输出 JSON" in system:
            return FakeMessage(
                json.dumps(
                    {
                        "buyer_strongest_evidence": ["买方证据 A"],
                        "seller_strongest_evidence": ["卖方证据 B"],
                        "disputed_points": ["争议点 C"],
                        "evidence_gaps": ["缺口 D"],
                        "conservative_summary": "保守总结，不构成交易建议。",
                        "disclaimer": "本报告不构成交易建议。",
                    },
                    ensure_ascii=False,
                )
            )
        if "买方角色" in system:
            return FakeMessage("买方证据：quote 支持偏积极观点。")
        if "卖方角色" in system:
            return FakeMessage("卖方证据：finance 暴露谨慎因素。")
        if "你是买方" in user:
            return FakeMessage("买方本轮观点。")
        return FakeMessage("卖方本轮观点。")


@pytest.fixture
def fake_v3_client() -> FakeV3Client:
    return FakeV3Client()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
