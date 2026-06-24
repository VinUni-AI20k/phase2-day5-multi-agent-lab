"""Benchmark for single-agent vs multi-agent runs."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def _total_cost(state: ResearchState) -> float | None:
    costs = [
        result.metadata.get("cost_usd")
        for result in state.agent_results
        if result.metadata.get("cost_usd") is not None
    ]
    return sum(costs) if costs else None


def _citation_coverage(state: ResearchState) -> float | None:
    """Fraction of sources actually referenced in the final answer (rough proxy)."""

    if not state.sources or not state.final_answer:
        return None
    cited = sum(
        1
        for source in state.sources
        if source.url and source.url in state.final_answer
    )
    return cited / len(state.sources)


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run ``runner`` and capture latency, cost, failure, and citation metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    coverage = _citation_coverage(state)
    notes_parts = [f"errors={len(state.errors)}"]
    if coverage is not None:
        notes_parts.append(f"citation_coverage={coverage:.0%}")
    if state.errors:
        notes_parts.append(f"failure={state.errors[0][:60]}")

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_total_cost(state),
        notes="; ".join(notes_parts),
    )
    return state, metrics
