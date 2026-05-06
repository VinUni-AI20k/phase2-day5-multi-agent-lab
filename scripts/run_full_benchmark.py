"""End-to-end benchmark runner that captures latency, cost, traces, and outputs.

Usage:
    python scripts/run_full_benchmark.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient

console = Console()
REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)
ARTIFACTS = REPORTS / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def baseline_runner(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    llm = LLMClient()
    response = llm.complete(
        "You are a knowledgeable AI. Answer in ~500 words with a Key Takeaways section.",
        query,
    )
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
    )
    return state


def multi_agent_runner(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    return MultiAgentWorkflow().run(state)


def save_artifacts(name: str, state: ResearchState) -> None:
    """Persist final answer, intermediate notes, and the trace as JSON."""
    folder = ARTIFACTS / name
    folder.mkdir(exist_ok=True)

    if state.final_answer:
        (folder / "final_answer.md").write_text(state.final_answer, encoding="utf-8")
    if state.research_notes:
        (folder / "research_notes.md").write_text(state.research_notes, encoding="utf-8")
    if state.analysis_notes:
        (folder / "analysis_notes.md").write_text(state.analysis_notes, encoding="utf-8")

    trace_payload = {
        "query": state.request.query,
        "route_history": state.route_history,
        "iterations": state.iteration,
        "trace": state.trace,
        "agent_results": [r.model_dump() for r in state.agent_results],
        "sources": [s.model_dump() for s in state.sources],
        "errors": state.errors,
    }
    (folder / "trace.json").write_text(
        json.dumps(trace_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    settings = get_settings()
    log_path = str(REPORTS / "run.log")
    configure_logging(settings.log_level, log_file=log_path)
    console.print(f"[dim]Logging to {log_path}[/dim]\n")

    query = "Research GraphRAG state-of-the-art and write a 500-word summary"
    console.print(f"[bold cyan]Query:[/bold cyan] {query}\n")

    console.print("[bold]Running single-agent baseline...[/bold]")
    baseline_state, baseline_metrics = run_benchmark("single-agent", query, baseline_runner)
    save_artifacts("single-agent", baseline_state)

    console.print("[bold]Running multi-agent workflow...[/bold]")
    multi_state, multi_metrics = run_benchmark("multi-agent", query, multi_agent_runner)
    save_artifacts("multi-agent", multi_state)

    table = Table(title="Benchmark Results")
    table.add_column("Run")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Quality /10", justify="right")
    for m in (baseline_metrics, multi_metrics):
        table.add_row(
            m.run_name,
            f"{m.latency_seconds:.2f}",
            f"{m.estimated_cost_usd:.5f}" if m.estimated_cost_usd is not None else "-",
            f"{m.quality_score:.1f}" if m.quality_score is not None else "-",
        )
    console.print(table)

    summary = {
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "model": settings.openai_model,
        "results": [
            baseline_metrics.model_dump(),
            multi_metrics.model_dump(),
        ],
    }
    (REPORTS / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"\n[green]Artifacts saved under {ARTIFACTS}[/green]")
    console.print(f"[green]Summary saved to {REPORTS / 'benchmark_summary.json'}[/green]")


if __name__ == "__main__":
    main()
