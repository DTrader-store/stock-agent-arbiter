from __future__ import annotations

from tests.conftest import FakeV3Client

from stock_agent_arbiter.v3_adapter import MarketDataAdapter
from stock_agent_arbiter.workflow import StockArbiterWorkflow


def test_workflow_generates_three_rounds_and_structured_summary(fake_llm) -> None:
    workflow = StockArbiterWorkflow(MarketDataAdapter(FakeV3Client()), fake_llm)

    state = workflow.run("600519")

    assert state["aborted"] is False
    assert len(state["debate"]) == 3
    assert [turn.round_number for turn in state["debate"]] == [1, 2, 3]
    assert state["buyer_evidence"].role == "buyer"
    assert state["seller_evidence"].role == "seller"
    assert state["summary"].buyer_strongest_evidence == ["买方证据 A"]
    assert state["summary"].disclaimer == "本报告不构成交易建议。"


def test_workflow_continues_when_one_source_is_missing(fake_llm) -> None:
    workflow = StockArbiterWorkflow(MarketDataAdapter(FakeV3Client(empty="quote")), fake_llm)

    state = workflow.run("600519")

    assert state["aborted"] is False
    assert len(state["debate"]) == 3
    assert state["missing_data"] == {"quote": "empty data"}


def test_workflow_continues_when_ranking_sources_are_missing(fake_llm) -> None:
    workflow = StockArbiterWorkflow(
        MarketDataAdapter(FakeV3Client(empty={"ranking_stocks", "ranking_boards"})),
        fake_llm,
    )

    state = workflow.run("600519")

    assert state["aborted"] is False
    assert len(state["debate"]) == 3
    assert state["missing_data"] == {
        "ranking_stocks": "empty data",
        "ranking_boards": "empty data",
    }
    assert "ranking_stocks" not in fake_llm.calls[0][1][1]
    assert "ranking_boards" not in fake_llm.calls[0][1][1]


def test_workflow_aborts_when_all_sources_are_missing(fake_llm) -> None:
    workflow = StockArbiterWorkflow(
        MarketDataAdapter(
            FakeV3Client(
                empty={
                    "quote",
                    "kline",
                    "details",
                    "trends",
                    "finance",
                    "ranking_stocks",
                    "ranking_boards",
                }
            )
        ),
        fake_llm,
    )

    state = workflow.run("600519")

    assert state["aborted"] is True
    assert state["debate"] == []
    assert "quote: empty data" in state["summary"].evidence_gaps
    assert fake_llm.calls == []
