from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_to_researcher_first() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state = SupervisorAgent().run(state)
    assert state.route_history[-1] == "researcher"


def test_supervisor_routes_in_order() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "notes"
    state.analysis_notes = "analysis"
    state = SupervisorAgent().run(state)
    assert state.route_history[-1] == "writer"


def test_supervisor_routes_to_critic_after_answer() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "notes"
    state.analysis_notes = "analysis"
    state.final_answer = "answer"
    state = SupervisorAgent().run(state)
    assert state.route_history[-1] == "critic"


def test_supervisor_stops_when_done() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "notes"
    state.analysis_notes = "analysis"
    state.final_answer = "answer"
    state.critique = "VERDICT: PASS"
    state = SupervisorAgent().run(state)
    assert state.route_history[-1] == "done"
