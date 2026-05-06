# Design Notes — Multi-Agent Research System

**Author:** Trịnh Kế Tiến — 2A202600500
**Date:** 2026-05-06

## Problem

Build a research assistant that takes an open-ended technical query and returns a ~500-word, source-cited briefing. The system must be auditable: at any point we should be able to inspect what was searched, what was inferred, and what was finally written.

## Why multi-agent?

A single LLM call can answer the query, but it conflates three different tasks (search, analysis, writing) under one prompt. That makes it hard to:

1. Swap the search backend without rewriting the prompt.
2. Reason about why a claim ended up in the answer (no separation between "what we found" and "what we concluded").
3. Add guardrails per stage (e.g., a citation check that only inspects the writer's output).

Splitting into Supervisor + Researcher + Analyst + Writer makes each stage independently testable, replaceable, and traceable. The trade-off is more LLM calls (higher latency and cost), which we accept for this lab because output quality and auditability matter more than speed.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Decide next worker or stop | `ResearchState` | append to `route_history` | infinite loop → mitigated by `MAX_ITERATIONS=6` |
| Researcher | Search + structured notes | `request.query` | `state.sources`, `state.research_notes` | empty search → mock fallback in `SearchClient` |
| Analyst | Critical analysis of notes | `state.research_notes` | `state.analysis_notes` | hallucinated claims → strict prompt asking for evidence quality labels |
| Writer | Final answer with citations | research + analysis + sources | `state.final_answer` | hallucinated `[Source N]` → grounding via explicit source list in prompt |

## Shared state

Defined in [state.py](../src/multi_agent_research_lab/core/state.py):

| Field | Why we need it |
|---|---|
| `request: ResearchQuery` | Original input (query, audience, max_sources) |
| `iteration` | Drives the supervisor's max-iter guardrail |
| `route_history` | Reproducible debugging: who ran, in what order |
| `sources: list[SourceDocument]` | Ground truth for the writer's citations |
| `research_notes` | Analyst's input |
| `analysis_notes` | Writer's input |
| `final_answer` | The deliverable |
| `agent_results` | Per-agent metadata (tokens, cost) for benchmarking |
| `trace: list[dict]` | Lightweight observability, also exported to LangSmith if configured |
| `errors: list[str]` | Failure surface for the benchmark scorer |

## Routing policy

Implemented in [supervisor.py](../src/multi_agent_research_lab/agents/supervisor.py). The supervisor inspects the state in priority order:

```
if iteration >= MAX_ITERATIONS:        → done   (safety)
elif research_notes is None:           → researcher
elif analysis_notes is None:           → analyst
elif final_answer is None:             → writer
else:                                  → done
```

This is deliberately rule-based, not LLM-based. Rationale: routing decisions for this task are simple and benefit from being deterministic and zero-cost. An LLM-based supervisor would add latency and cost for no quality gain. We can switch to an LLM router later if dynamic skill selection becomes necessary.

The graph is implemented with LangGraph (`StateGraph`) in [workflow.py](../src/multi_agent_research_lab/graph/workflow.py):

```text
START → supervisor ─┬─ researcher → supervisor
                    ├─ analyst   → supervisor
                    ├─ writer    → supervisor
                    └─ END
```

Every worker returns to the supervisor so routing remains centralised.

## Guardrails

- **Max iterations**: 6 (hard cap in supervisor)
- **Timeout**: 60s per LLM call (passed to OpenAI client)
- **Retry**: `tenacity` with exponential backoff, 3 attempts
- **Fallback**: search → mock when no API key
- **Validation**: Pydantic schemas on every input/output; Pydantic state used as LangGraph state
- **Cost logging**: every LLM call records `input_tokens`, `output_tokens`, `cost_usd` into `agent_results`

## Benchmark plan

Defined in [benchmark.py](../src/multi_agent_research_lab/evaluation/benchmark.py).

| Metric | Method | Why |
|---|---|---|
| Latency | `perf_counter()` wall-clock | User-facing speed |
| Cost (USD) | Token × per-1M price | Economics of scaling up |
| Quality (0-10) | Heuristic on output completeness | Cheap proxy for peer review |
| Citation coverage | Count of `[Source N]` markers vs `state.sources` (planned) | Hallucination guard |
| Failure rate | `len(state.errors)` over total runs | Reliability |

Test queries (in [lab_default.yaml](../configs/lab_default.yaml)):

1. "Research GraphRAG state-of-the-art and write a 500-word summary"
2. "Compare single-agent and multi-agent workflows for customer support"
3. "Summarize production guardrails for LLM agents"

Expected outcome: multi-agent wins on quality and citation coverage; single-agent wins on latency and cost. See [benchmark_report.md](../reports/benchmark_report.md) for measured numbers.
