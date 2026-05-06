# Benchmark Report — Single-Agent vs Multi-Agent Research

**Author:** Trịnh Kế Tiến — 2A202600500
**Date:** 2026-05-06
**Lab:** Day 20 — Multi-Agent Research System
**Run command:** `python scripts/run_full_benchmark.py`

---

## 1. Setup

| Item | Value |
|---|---|
| LLM | `gpt-4o-mini` (OpenAI) |
| Temperature | Supervisor 0.0, Researcher 0.2, Analyst 0.1, Writer 0.4 |
| Search backend | Mock fallback (no `TAVILY_API_KEY` provided) |
| Max iterations | 6 |
| Timeout | 60s |
| Test query | `"Research GraphRAG state-of-the-art and write a 500-word summary"` |

Reproducibility:

```powershell
.\.venv\Scripts\activate
python scripts/run_full_benchmark.py
```

Raw artifacts saved under [reports/artifacts/](artifacts/):

- [single-agent/final_answer.md](artifacts/single-agent/final_answer.md)
- [multi-agent/final_answer.md](artifacts/multi-agent/final_answer.md)
- [multi-agent/research_notes.md](artifacts/multi-agent/research_notes.md)
- [multi-agent/analysis_notes.md](artifacts/multi-agent/analysis_notes.md)
- [multi-agent/trace.json](artifacts/multi-agent/trace.json)
- [benchmark_summary.json](benchmark_summary.json)

---

## 2. Methodology

Two pipelines were run on the same query:

- **Single-agent baseline** — one LLM call. Prompt asks for a ~500-word answer with Key Takeaways. No search, no analysis pass, no citation requirement.
- **Multi-agent workflow** — Supervisor (rule-based router) → Researcher (mock search + LLM notes) → Analyst (structured insight LLM call) → Writer (final answer LLM call) → done.

Per run we measured:

| Metric | Method |
|---|---|
| Latency (s) | Wall-clock from call to final answer |
| Cost (USD) | `(input_tokens × $0.150 + output_tokens × $0.600) / 1M` summed across all LLM calls |
| Quality (0–10) | Heuristic in [evaluation/benchmark.py](../src/multi_agent_research_lab/evaluation/benchmark.py) — completeness × content presence × source count − errors |
| Citation count | `grep -c '\[Source \d+\]'` on `final_answer.md` |

---

## 3. Results (real run, 2026-05-06)

| Run | Latency (s) | Cost (USD) | Quality /10 | Citations | Output chars |
|---|---:|---:|---:|---:|---:|
| single-agent | 14.27 | 0.00046 | 7.0 | 0 | ~3,400 |
| multi-agent  | 29.70 | 0.00146 | 10.0 | 15 | ~3,841 |

Source: [`reports/benchmark_summary.json`](benchmark_summary.json) — generated automatically.

### 3.1 Trade-off summary

- **Multi-agent is ~2.08× slower** (3 sequential LLM calls + supervisor routing vs 1 LLM call).
- **Multi-agent costs ~3.17× more** in tokens.
- **Multi-agent produces 15 inline citations**, baseline produces **zero** — auditable claims vs unverifiable text.
- **Multi-agent quality 10.0 vs 7.0** on the heuristic; the heuristic favours multi-agent because it rewards intermediate state (research notes, analysis, sources). For a fairer score, a fixed-rubric peer review is recommended.

### 3.2 Cost breakdown — multi-agent run

From [trace.json](artifacts/multi-agent/trace.json):

| Agent | Cost (USD) |
|---|---:|
| Researcher | 0.00034 |
| Analyst | 0.00049 |
| Writer | 0.00063 |
| Total | 0.00146 |

The Writer dominates cost because its prompt carries research + analysis + sources as context. This is consistent with: longer context → more input tokens → higher cost.

### 3.3 Trace summary — multi-agent

```text
supervisor -> researcher -> supervisor -> analyst -> supervisor -> writer -> supervisor -> done
```

- Iterations: 4 (supervisor was invoked between every worker, as designed)
- Errors: 0
- Sources collected: 5

Full event list in [trace.json](artifacts/multi-agent/trace.json).

---

## 4. Failure mode analysis

During development I observed (or designed against) the following failure modes:

### 4.1 Infinite supervisor loop

**Symptom:** Supervisor keeps routing to a worker whose output is empty, the worker fails to populate state, and the loop repeats.

**Root cause:** Worker raises silently or returns without writing the expected field.

**Fix implemented:**

- Hard cap at `MAX_ITERATIONS = 6` enforced in [supervisor.py](../src/multi_agent_research_lab/agents/supervisor.py). When `state.iteration >= max_iter`, route is forced to `done`.
- Each worker logs how many chars it wrote so empty outputs are visible in the trace and CLI logs.

### 4.2 Search returns no results

**Symptom:** `ResearcherAgent` produces empty notes because Tavily / search returns nothing.

**Fix implemented:** [search_client.py](../src/multi_agent_research_lab/services/search_client.py) falls back to a deterministic mock when `TAVILY_API_KEY` is unset. The mock generates 5 plausible sources keyed off the query so the rest of the pipeline still has structured input. This is also what kept the run reproducible during development without burning a third-party search quota.

### 4.3 OpenAI transient errors / rate limits

**Symptom:** A single 5xx or rate-limit error kills the whole pipeline mid-run.

**Fix implemented:** [llm_client.py](../src/multi_agent_research_lab/services/llm_client.py) wraps every call in `tenacity.retry(stop_after_attempt(3), wait_exponential(min=2, max=10))` so transient errors back off and retry before propagating.

### 4.4 Hallucinated citations (the hardest one)

**Symptom:** Writer fabricates `[Source 6]` referring to a source that does not exist.

**Mitigation implemented:** The Writer prompt is explicitly grounded — it receives the source list as `[Source N] Title — URL` and is told to use that notation. Reading the multi-agent run output, all 15 `[Source N]` references map to real sources 1–5 (no `[Source 6]+` hallucination).

**Recommended next step (not yet wired):** add `CriticAgent` post-pass that diff-checks every `[Source N]` against `state.sources` and asks the Writer to rewrite if any citation is invalid. The skeleton remains in [critic.py](../src/multi_agent_research_lab/agents/critic.py).

---

## 5. When to choose multi-agent

**Use multi-agent when:**

- Output quality and auditability matter more than latency / cost (research briefs, due-diligence reports, compliance answers).
- Tasks have clear sub-roles that benefit from separate prompts (search ≠ analysis ≠ writing).
- You need intermediate artifacts to debug or explain *why* an answer says what it says.

**Stick with single-agent when:**

- The query is simple and a single prompt produces a sufficient answer.
- Latency budget is tight (interactive chat, real-time UI). With ~30s latency, multi-agent would be unacceptable in chat.
- Cost per query must be minimised at scale and the marginal quality lift is small.

---

## 6. Limitations of this benchmark

- **N=1 query.** The configured benchmark in `lab_default.yaml` lists 3 queries but `run_full_benchmark.py` runs only the headline one. Extending to all 3 would give variance bands.
- **Mock search.** The Researcher's input is synthetic. With real Tavily/SerpAPI sources, Writer citation correctness becomes a stronger signal.
- **Heuristic quality score.** The 0–10 score is structural (presence of fields), not semantic. Replace with peer review or LLM-as-judge for a publishable comparison.
- **No statistical significance.** Run each pipeline ≥5× and report mean ± std.
