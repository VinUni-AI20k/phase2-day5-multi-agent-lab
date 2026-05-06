"""Researcher agent — collects sources and writes research notes."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a meticulous research agent. Given a query and a list of source snippets,
write concise, structured research notes covering:
- Key definitions and concepts
- Main findings or claims from the sources
- Gaps or limitations mentioned
- Relevant citations (use [Source N] notation)

Be factual. Do not invent information beyond what the sources provide."""


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._search = SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate state.sources and state.research_notes."""
        query = state.request.query
        logger.info("Researcher: searching for '%s'", query)

        sources = self._search.search(query, max_results=state.request.max_sources)
        state.sources = sources

        snippets = "\n\n".join(
            f"[Source {i+1}] {s.title}\n{s.snippet}" for i, s in enumerate(sources)
        )
        user_prompt = f"Query: {query}\n\nSources:\n{snippets}"

        response = self._llm.complete(_SYSTEM_PROMPT, user_prompt)
        state.research_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=response.content,
                metadata={
                    "sources_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("researcher", {"sources": len(sources), "cost_usd": response.cost_usd})
        logger.info("Researcher: done. %d sources, %d chars of notes.", len(sources), len(state.research_notes))
        return state
