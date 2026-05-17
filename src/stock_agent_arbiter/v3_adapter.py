from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from .models import EvidenceSnapshot


class V3ReadOnlyClient(Protocol):
    def quote(self, code: str) -> Any: ...

    def kline(self, code: str, query: Mapping[str, Any] | None = None) -> Any: ...

    def details(self, code: str, query: Mapping[str, Any] | None = None) -> Any: ...

    def trends(self, code: str, query: Mapping[str, Any] | None = None) -> Any: ...

    def finance(self, code: str) -> Any: ...

    def ranking_stocks(self, query: Mapping[str, Any] | None = None) -> Any: ...

    def ranking_boards(self, query: Mapping[str, Any] | None = None) -> Any: ...


class MarketDataAdapter:
    """Read-only evidence pack around DTrader V3 SDK."""

    def __init__(self, client: V3ReadOnlyClient) -> None:
        self._client = client

    def fetch_basic_evidence(self, code: str) -> EvidenceSnapshot:
        code = code.strip()
        sources: dict[str, Any] = {}
        missing: dict[str, str] = {}
        fetches: dict[str, Callable[[], Any]] = {
            "quote": lambda: self._client.quote(code),
            "kline": lambda: self._client.kline(code, {"period": "day"}),
            "details": lambda: self._client.details(code),
            "trends": lambda: self._client.trends(code),
            "finance": lambda: self._client.finance(code),
            "ranking_stocks": lambda: self._client.ranking_stocks({"page": 1, "pageSize": 10}),
            "ranking_boards": lambda: self._client.ranking_boards({"page": 1, "pageSize": 10}),
        }

        for name, fetch in fetches.items():
            try:
                response = fetch()
            except Exception as exc:  # pragma: no cover - exact SDK exceptions vary by transport.
                sources[name] = None
                missing[name] = str(exc)
                continue

            empty_reason = _empty_reason(response)
            if empty_reason:
                sources[name] = response
                missing[name] = empty_reason
            else:
                sources[name] = response

        return EvidenceSnapshot(code=code, sources=sources, missing=missing)


def validate_stock_code(code: str) -> str:
    normalized = code.strip()
    if not normalized:
        raise ValueError("stock code must not be empty")
    return normalized


def _empty_reason(response: Any) -> str | None:
    if response is None:
        return "empty response"
    if isinstance(response, dict):
        status_code = response.get("code")
        if isinstance(status_code, int) and status_code != 0:
            message = response.get("msg") or response.get("message") or "non-zero response code"
            return f"code={status_code}: {message}"
        data = response.get("data", response)
        if _is_empty(data):
            return "empty data"
        return None
    if _is_empty(response):
        return "empty response"
    return None


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}
