"""Tests for the benchmark scoring and runner."""

from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
    SourceDocument,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import _score_quality, run_benchmark


def _make_full_state() -> ResearchState:
    state = ResearchState(request=ResearchQuery(query="Test query about multi-agent"))
    state.sources = [
        SourceDocument(title="A", snippet="..."),
        SourceDocument(title="B", snippet="..."),
    ]
    state.research_notes = "Some research notes"
    state.analysis_notes = "Some analysis"
    state.final_answer = " ".join(["word"] * 250)
    state.agent_results = [
        AgentResult(agent=AgentName.RESEARCHER, content="r", metadata={"cost_usd": 0.001}),
        AgentResult(agent=AgentName.ANALYST, content="a", metadata={"cost_usd": 0.002}),
        AgentResult(agent=AgentName.WRITER, content="w", metadata={"cost_usd": 0.003}),
    ]
    return state


def test_quality_score_for_complete_state() -> None:
    score = _score_quality(_make_full_state())
    assert 0 < score <= 10


def test_quality_score_for_empty_state() -> None:
    state = ResearchState(request=ResearchQuery(query="Empty test query"))
    assert _score_quality(state) == 0.0


def test_run_benchmark_records_metrics() -> None:
    def fake_runner(query: str) -> ResearchState:
        return _make_full_state()

    state, metrics = run_benchmark("test-run", "Some test query", fake_runner)
    assert metrics.run_name == "test-run"
    assert metrics.latency_seconds >= 0
    assert metrics.estimated_cost_usd is not None
    assert metrics.estimated_cost_usd > 0
    assert metrics.quality_score is not None and metrics.quality_score > 0
    assert state.final_answer
