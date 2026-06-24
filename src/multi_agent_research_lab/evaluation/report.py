"""Benchmark report rendering."""

from __future__ import annotations

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    query: str | None = None,
    answers: dict[str, str | None] | None = None,
    critique: str | None = None,
) -> str:
    """Render benchmark metrics (and optional answers) to markdown."""

    lines = ["# Benchmark Report", ""]
    if query:
        lines += [f"**Query:** {query}", ""]

    lines += [
        "## Metrics",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.6f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |"
        )

    if answers:
        lines += ["", "## Answers", ""]
        for name, answer in answers.items():
            lines += [f"### {name}", "", (answer or "_(no answer)_"), ""]

    if critique:
        lines += ["", "## Critic review (multi-agent)", "", critique, ""]

    lines += [
        "",
        "## Quality scoring",
        "",
        "Quality is left blank above — fill it via peer review using "
        "`docs/peer_review_rubric.md` (0-10).",
        "",
        "## Failure mode",
        "",
        "_TODO: describe one failure mode you observed and how you fixed it._",
    ]
    return "\n".join(lines) + "\n"
