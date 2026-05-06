"""LangGraph multi-agent workflow."""

import logging

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

_SUPERVISOR = "supervisor"
_RESEARCHER = "researcher"
_ANALYST = "analyst"
_WRITER = "writer"
_CRITIC = "critic"


def _route_from_supervisor(state: ResearchState) -> str:
    """Read the last route written by the supervisor and return it as the next node."""
    if not state.route_history:
        return END  # type: ignore[return-value]
    last = state.route_history[-1]
    return END if last == "done" else last  # type: ignore[return-value]


class MultiAgentWorkflow:
    """Builds and runs the multi-agent LangGraph workflow."""

    def __init__(self) -> None:
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent()
        self._analyst = AnalystAgent()
        self._writer = WriterAgent()
        self._critic = CriticAgent()

    def build(self) -> object:
        """Create the LangGraph StateGraph."""
        graph = StateGraph(ResearchState)

        # Wrap each agent so it accepts and returns a dict (LangGraph requirement)
        def supervisor_node(state: ResearchState) -> ResearchState:
            return self._supervisor.run(state)

        def researcher_node(state: ResearchState) -> ResearchState:
            return self._researcher.run(state)

        def analyst_node(state: ResearchState) -> ResearchState:
            return self._analyst.run(state)

        def writer_node(state: ResearchState) -> ResearchState:
            return self._writer.run(state)

        def critic_node(state: ResearchState) -> ResearchState:
            return self._critic.run(state)

        graph.add_node(_SUPERVISOR, supervisor_node)
        graph.add_node(_RESEARCHER, researcher_node)
        graph.add_node(_ANALYST, analyst_node)
        graph.add_node(_WRITER, writer_node)
        graph.add_node(_CRITIC, critic_node)

        # Entry point → supervisor
        graph.set_entry_point(_SUPERVISOR)

        # Supervisor conditionally routes to a worker or END
        graph.add_conditional_edges(
            _SUPERVISOR,
            _route_from_supervisor,
            {
                _RESEARCHER: _RESEARCHER,
                _ANALYST: _ANALYST,
                _WRITER: _WRITER,
                _CRITIC: _CRITIC,
                END: END,
            },
        )

        # After each worker, return to supervisor for next routing decision
        graph.add_edge(_RESEARCHER, _SUPERVISOR)
        graph.add_edge(_ANALYST, _SUPERVISOR)
        graph.add_edge(_WRITER, _SUPERVISOR)
        graph.add_edge(_CRITIC, _SUPERVISOR)

        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Compile and invoke the graph, returning the final ResearchState."""
        app = self.build()
        logger.info("Starting multi-agent workflow for query: %s", state.request.query)
        result = app.invoke(state)
        if isinstance(result, ResearchState):
            return result
        # LangGraph may return a dict when using Pydantic state
        return ResearchState(**result) if isinstance(result, dict) else result
