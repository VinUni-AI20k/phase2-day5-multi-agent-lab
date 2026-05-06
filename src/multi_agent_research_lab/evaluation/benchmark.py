"""Benchmark runner for single-agent vs multi-agent comparison."""

import logging
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

Runner = Callable[[str], ResearchState]


def _estimate_total_cost(state: ResearchState) -> float | None:
    costs = [r.metadata.get("cost_usd") for r in state.agent_results]
    if any(c is None for c in costs):
        return None
    return sum(float(c) for c in costs)  # type: ignore[arg-type]


def _score_quality(state: ResearchState) -> float:
    """Heuristic quality score 0–10 based on output completeness."""
    score = 0.0
    if state.final_answer:
        score += 4.0
        word_count = len(state.final_answer.split())
        score += min(word_count / 100, 3.0)  # up to +3 for length
    if state.research_notes:
        score += 1.5
    if state.analysis_notes:
        score += 1.5
    if state.sources:
        score += min(len(state.sources) * 0.2, 1.0)
    if state.errors:
        score -= len(state.errors) * 0.5
    return max(0.0, min(score, 10.0))


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, cost, and quality for one run."""
    logger.info("Benchmarking [%s] query='%s'", run_name, query)
    started = perf_counter()
    try:
        state = runner(query)
    except Exception as exc:
        logger.error("Runner [%s] failed: %s", run_name, exc)
        raise

    latency = perf_counter() - started
    cost = _estimate_total_cost(state)
    quality = _score_quality(state)

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        notes=f"routes={state.route_history}, errors={len(state.errors)}",
    )
    logger.info("[%s] latency=%.2fs cost=$%.5f quality=%.1f", run_name, latency, cost or 0, quality)
    return state, metrics
