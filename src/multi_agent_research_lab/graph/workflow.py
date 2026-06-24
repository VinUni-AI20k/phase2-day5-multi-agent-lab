"""Multi-agent workflow orchestration.

A simple, debuggable state machine: the supervisor picks the next route and the
workflow dispatches to the matching worker. Guardrails (max iterations, failure
fallback) keep the loop bounded. Swap in LangGraph later if you need parallelism.
"""

from __future__ import annotations

import logging

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent workflow."""

    def __init__(self) -> None:
        llm = LLMClient()
        search = SearchClient()
        self._supervisor = SupervisorAgent()
        self._workers = {
            "researcher": ResearcherAgent(llm, search),
            "analyst": AnalystAgent(llm),
            "writer": WriterAgent(llm),
            "critic": CriticAgent(llm),
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the workflow until the supervisor routes to ``done``."""

        while True:
            state = self._supervisor.run(state)
            route = state.route_history[-1]
            if route == "done":
                break

            worker = self._workers[route]
            with trace_span(route) as span:
                try:
                    state = worker.run(state)
                except Exception as exc:  # fallback instead of crashing the run
                    logger.exception("Agent %s failed", route)
                    state.errors.append(f"{route}: {exc}")
                    span["attributes"]["error"] = str(exc)
                    break

        return state
