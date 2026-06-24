"""Researcher agent."""

from __future__ import annotations

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

_SYSTEM_PROMPT = (
    "You are a meticulous researcher. Summarize the provided sources into concise "
    "research notes. Keep inline citations using the source URLs. Do not invent facts "
    "that are not supported by the sources."
)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, llm: LLMClient, search: SearchClient) -> None:
        self._llm = llm
        self._search = search

    def run(self, state: ResearchState) -> ResearchState:
        sources = self._search.search(state.request.query, state.request.max_sources)
        state.sources.extend(sources)

        context = "\n".join(
            f"- {s.title}: {s.snippet} ({s.url})" for s in sources
        )
        response = self._llm.complete(
            _SYSTEM_PROMPT,
            f"Query: {state.request.query}\n\nSources:\n{context}",
        )
        state.research_notes = response.content
        state.add_trace_event(
            self.name,
            {"n_sources": len(sources), "cost_usd": response.cost_usd},
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=response.content,
                metadata={
                    "cost_usd": response.cost_usd,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "n_sources": len(sources),
                },
            )
        )
        return state
