"""Analyst agent — turns research notes into structured insights."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an analytical agent. Given research notes on a topic, produce a structured analysis:
1. **Key Claims** — list the 3-5 strongest claims with evidence quality (strong / weak / contested).
2. **Comparative Insights** — compare different viewpoints or approaches.
3. **Evidence Gaps** — flag missing data, weak citations, or contested facts.
4. **Recommended Focus** — which aspects deserve most attention in a final answer.

Be critical and objective. Highlight uncertainty where it exists."""


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.analysis_notes."""
        if not state.research_notes:
            logger.warning("Analyst called without research_notes — skipping.")
            state.analysis_notes = "(No research notes available to analyse.)"
            return state

        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Research Notes:\n{state.research_notes}"
        )

        response = self._llm.complete(_SYSTEM_PROMPT, user_prompt)
        state.analysis_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("analyst", {"cost_usd": response.cost_usd})
        logger.info("Analyst: done. %d chars of analysis.", len(state.analysis_notes))
        return state
