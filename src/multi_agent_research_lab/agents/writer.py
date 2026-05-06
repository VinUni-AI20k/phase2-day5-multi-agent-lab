"""Writer agent — produces the final answer."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a technical writer producing a final answer for {audience}.
Using the research notes and analyst insights provided, write a clear, well-structured response that:
- Directly answers the query in the opening paragraph.
- Uses headers and bullet points where appropriate.
- Includes source references (e.g. [Source 1]) where claims come from the research.
- Ends with a brief "Key Takeaways" section (3 bullets max).
- Target length: ~500 words."""


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.final_answer."""
        sources_block = ""
        if state.sources:
            sources_block = "\n\nSources available:\n" + "\n".join(
                f"[Source {i+1}] {s.title} — {s.url or 'no url'}"
                for i, s in enumerate(state.sources)
            )

        system = _SYSTEM_PROMPT.format(audience=state.request.audience)
        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Research Notes:\n{state.research_notes or '(none)'}\n\n"
            f"Analyst Insights:\n{state.analysis_notes or '(none)'}"
            f"{sources_block}"
        )

        response = self._llm.complete(system, user_prompt)
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
        state.add_trace_event("writer", {"cost_usd": response.cost_usd, "chars": len(state.final_answer)})
        logger.info("Writer: done. %d chars in final answer.", len(state.final_answer))
        return state
