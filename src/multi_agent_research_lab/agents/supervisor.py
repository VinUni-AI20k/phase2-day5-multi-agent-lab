"""Supervisor / router agent."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

_ROUTE_RESEARCHER = "researcher"
_ROUTE_ANALYST = "analyst"
_ROUTE_WRITER = "writer"
_ROUTE_CRITIC = "critic"
_ROUTE_DONE = "done"


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update state.route_history with the next route.

        Routing policy (in order):
        1. If max_iterations exceeded -> done (fallback safety).
        2. If no research_notes -> researcher.
        3. If no analysis_notes -> analyst.
        4. If no final_answer -> writer.
        5. If final_answer exists but critic has not run -> critic.
        6. Otherwise -> done.
        """
        settings = get_settings()
        max_iter = settings.max_iterations
        critic_ran = _ROUTE_CRITIC in state.route_history

        if state.iteration >= max_iter:
            logger.warning("Max iterations (%d) reached -- stopping.", max_iter)
            route = _ROUTE_DONE
        elif state.research_notes is None:
            route = _ROUTE_RESEARCHER
        elif state.analysis_notes is None:
            route = _ROUTE_ANALYST
        elif state.final_answer is None:
            route = _ROUTE_WRITER
        elif not critic_ran:
            route = _ROUTE_CRITIC
        else:
            route = _ROUTE_DONE

        logger.info("Supervisor -> %s (iteration %d)", route, state.iteration)
        state.record_route(route)
        state.add_trace_event("supervisor", {"route": route, "iteration": state.iteration})
        return state
