from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from pydantic import BaseModel, Field

JsonMap = dict[str, Any]


class EvidenceSnapshot(BaseModel):
    code: str
    sources: dict[str, Any] = Field(default_factory=dict)
    missing: dict[str, str] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return not self.missing


class RoleEvidence(BaseModel):
    role: str
    stance: str
    content: str


class DebateTurn(BaseModel):
    round_number: int
    buyer_argument: str
    seller_argument: str


class ArbiterSummary(BaseModel):
    buyer_strongest_evidence: list[str] = Field(default_factory=list)
    seller_strongest_evidence: list[str] = Field(default_factory=list)
    disputed_points: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    conservative_summary: str = ""
    disclaimer: str = "本报告不构成交易建议。"


class ArbiterState(TypedDict, total=False):
    code: str
    snapshot: EvidenceSnapshot
    aborted: bool
    missing_data: dict[str, str]
    buyer_evidence: RoleEvidence
    seller_evidence: RoleEvidence
    debate: list[DebateTurn]
    summary: ArbiterSummary


class StreamUpdate(TypedDict):
    node: str
    update: dict[str, Any]
    state: ArbiterState


class ReadOnlyV3Client(TypedDict, total=False):
    """Documentation-only shape for the allowed V3 surface."""

    quote: NotRequired[Any]
    kline: NotRequired[Any]
    details: NotRequired[Any]
    trends: NotRequired[Any]
    finance: NotRequired[Any]
    ranking_stocks: NotRequired[Any]
    ranking_boards: NotRequired[Any]


def compact_json(value: Any, *, max_chars: int = 12_000) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... [truncated {len(text) - max_chars} chars]"


def compact_sources(sources: Mapping[str, Any], *, per_source_chars: int = 2_500) -> str:
    compacted = {name: compact_json(value, max_chars=per_source_chars) for name, value in sources.items()}
    return compact_json(compacted, max_chars=20_000)
