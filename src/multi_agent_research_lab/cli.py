"""Command-line entrypoint for the lab."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline (Supervisor → Writer only, no search)."""
    _init()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)

    llm = LLMClient()
    system = (
        "You are a knowledgeable AI assistant. Answer the user's research query directly, "
        "clearly, and in about 500 words. Include a brief Key Takeaways section at the end."
    )
    response = llm.complete(system, query)
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
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the full multi-agent workflow (Supervisor → Researcher → Analyst → Writer)."""
    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc

    console.print(Panel.fit(result.final_answer or "(no answer)", title="Multi-Agent Answer"))
    console.print(f"\n[bold]Route history:[/bold] {' -> '.join(result.route_history)}")
    console.print(f"[bold]Iterations:[/bold] {result.iteration}")


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")] = (
        "Research GraphRAG state-of-the-art and write a 500-word summary"
    ),
    output: Annotated[str, typer.Option("--output", "-o")] = "reports/benchmark_report.md",
) -> None:
    """Compare single-agent baseline vs multi-agent and save a markdown report."""
    _init()

    def baseline_runner(q: str) -> ResearchState:
        st = ResearchState(request=ResearchQuery(query=q))
        llm = LLMClient()
        resp = llm.complete(
            "You are a knowledgeable AI. Answer in ~500 words with Key Takeaways.", q
        )
        st.final_answer = resp.content
        st.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=resp.content,
                metadata={"cost_usd": resp.cost_usd, "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens},
            )
        )
        return st

    def multi_agent_runner(q: str) -> ResearchState:
        st = ResearchState(request=ResearchQuery(query=q))
        return MultiAgentWorkflow().run(st)

    console.print("[bold cyan]Running single-agent baseline...[/bold cyan]")
    _, baseline_metrics = run_benchmark("single-agent", query, baseline_runner)

    console.print("[bold cyan]Running multi-agent workflow...[/bold cyan]")
    _, multi_metrics = run_benchmark("multi-agent", query, multi_agent_runner)

    all_metrics = [baseline_metrics, multi_metrics]
    report_md = render_markdown_report(all_metrics)

    store = LocalArtifactStore(Path(output).parent)
    saved = store.write_text(Path(output).name, report_md)
    console.print(f"\n[green]Report saved to {saved}[/green]")

    table = Table(title="Benchmark Results")
    table.add_column("Run")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Quality /10", justify="right")
    for m in all_metrics:
        table.add_row(
            m.run_name,
            f"{m.latency_seconds:.2f}",
            f"{m.estimated_cost_usd:.5f}" if m.estimated_cost_usd else "—",
            f"{m.quality_score:.1f}" if m.quality_score else "—",
        )
    console.print(table)


if __name__ == "__main__":
    app()
