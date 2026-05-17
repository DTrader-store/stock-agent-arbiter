from __future__ import annotations

import pytest

from stock_agent_arbiter.v3_adapter import MarketDataAdapter, validate_stock_code


def test_validate_stock_code_rejects_blank() -> None:
    with pytest.raises(ValueError):
        validate_stock_code("  ")


def test_market_data_adapter_calls_only_read_only_basic_pack(fake_v3_client) -> None:
    snapshot = MarketDataAdapter(fake_v3_client).fetch_basic_evidence("600519")

    assert snapshot.is_complete
    assert fake_v3_client.calls == [
        "quote",
        "kline",
        "details",
        "trends",
        "finance",
        "ranking_stocks",
        "ranking_boards",
    ]


def test_market_data_adapter_marks_empty_response_missing() -> None:
    from tests.conftest import FakeV3Client

    snapshot = MarketDataAdapter(FakeV3Client(empty="finance")).fetch_basic_evidence("600519")

    assert not snapshot.is_complete
    assert snapshot.missing == {"finance": "empty data"}
