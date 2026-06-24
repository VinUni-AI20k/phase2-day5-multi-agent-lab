"""Command-line entrypoint for the lab."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import dump_trace
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()

_BASELINE_SYSTEM_PROMPT = (
    "You are a thorough single-agent research assistant. Research the query, reason "
    "about it, and write a clear, well-cited answer in one pass."
)


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def run_baseline(query: str) -> ResearchState:
    """Single-agent baseline: one LLM call does everything."""

    state = ResearchState(request=ResearchQuery(query=query))
    llm = LLMClient()
    response = llm.complete(_BASELINE_SYSTEM_PROMPT, state.request.query)
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "cost_usd": response.cost_usd,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
    )
    return state


def run_multi_agent(query: str) -> ResearchState:
    """Multi-agent workflow: supervisor coordinates researcher, analyst, writer."""

    state = ResearchState(request=ResearchQuery(query=query))
    return MultiAgentWorkflow().run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline."""

    _init()
    state = run_baseline(query)
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    trace: Annotated[
        Path | None,
        typer.Option("--trace", help="Write the run trace to this JSON path"),
    ] = None,
) -> None:
    """Run the multi-agent workflow."""

    _init()
    try:
        state = run_multi_agent(query)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc

    console.print(Panel.fit(state.final_answer or "(no answer)", title="Multi-Agent Answer"))
    if state.critique:
        console.print(Panel.fit(state.critique, title="Critic Review", style="cyan"))
    if state.errors:
        console.print(Panel.fit("\n".join(state.errors), title="Errors", style="red"))
    if trace is not None:
        path = dump_trace(state, trace)
        console.print(Panel.fit(f"Trace written to {path}", style="green"))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Report output path")
    ] = Path("reports/benchmark_report.md"),
) -> None:
    """Run baseline and multi-agent, then write a comparison report."""

    _init()
    baseline_state, baseline_metrics = run_benchmark("baseline", query, run_baseline)
    multi_state, multi_metrics = run_benchmark("multi-agent", query, run_multi_agent)

    report = render_markdown_report(
        [baseline_metrics, multi_metrics],
        query=query,
        answers={
            "baseline": baseline_state.final_answer,
            "multi-agent": multi_state.final_answer,
        },
        critique=multi_state.critique,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    console.print(report)
    console.print(Panel.fit(f"Report written to {output}", style="green"))


if __name__ == "__main__":
    app()
