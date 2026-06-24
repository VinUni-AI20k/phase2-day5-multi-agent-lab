"""Supervisor / router."""

from __future__ import annotations

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop.

    Routing policy is field-driven: run each stage once, in order, until the final
    answer exists. ``max_iterations`` is enforced as a hard stop to prevent loops.
    """

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        settings = get_settings()

        if state.errors or state.iteration >= settings.max_iterations:
            next_route = "done"
        elif state.research_notes is None:
            next_route = "researcher"
        elif state.analysis_notes is None:
            next_route = "analyst"
        elif state.final_answer is None:
            next_route = "writer"
        elif state.critique is None:
            next_route = "critic"
        else:
            next_route = "done"

        state.record_route(next_route)
        state.add_trace_event(self.name, {"next": next_route, "iteration": state.iteration})
        return state
