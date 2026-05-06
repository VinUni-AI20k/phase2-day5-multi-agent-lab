"""Critic agent — validates the writer's citations against the actual source list."""

import logging
import re

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"\[Source\s+(\d+)\]")


class CriticAgent(BaseAgent):
    """Fact-check pass: verify every [Source N] reference points to a real source.

    Does not call an LLM — it's deterministic and free, so it can run on every output.
    Records findings into state.errors and a structured trace event.
    """

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        if not state.final_answer:
            logger.warning("Critic called without final_answer — skipping.")
            return state

        valid_indices = set(range(1, len(state.sources) + 1))
        cited = [int(m) for m in _CITATION_PATTERN.findall(state.final_answer)]
        unique_cited = set(cited)

        invalid = sorted(unique_cited - valid_indices)
        unused_sources = sorted(valid_indices - unique_cited)
        coverage = (len(unique_cited & valid_indices) / len(valid_indices)) if valid_indices else 0.0

        if invalid:
            msg = f"Critic: {len(invalid)} hallucinated citations: {invalid}"
            logger.warning(msg)
            state.errors.append(msg)

        findings = {
            "total_citations": len(cited),
            "unique_citations": len(unique_cited),
            "valid_source_count": len(valid_indices),
            "invalid_citations": invalid,
            "unused_sources": unused_sources,
            "coverage_ratio": round(coverage, 3),
        }
        state.add_trace_event("critic", findings)
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=f"Citation audit: {findings}",
                metadata=findings,
            )
        )
        logger.info(
            "Critic: %d total citations, %d unique, %d invalid, coverage %.0f%%",
            len(cited), len(unique_cited), len(invalid), coverage * 100,
        )
        return state
