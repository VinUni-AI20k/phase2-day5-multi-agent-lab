"""Critic agent: fact-check, citation coverage, and hallucination review."""

from __future__ import annotations

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

_SYSTEM_PROMPT = (
    "You are a rigorous critic. Review the final answer against the research notes and "
    "the listed sources. Check: (1) factual support — flag any claim not backed by the "
    "sources, (2) citation coverage — note claims missing a citation, (3) potential "
    "hallucinations. Respond with a short bullet-point critique and a verdict line "
    "'VERDICT: PASS' or 'VERDICT: REVISE'."
)


class CriticAgent(BaseAgent):
    """Validates the final answer and records findings."""

    name = "critic"

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, state: ResearchState) -> ResearchState:
        source_list = "\n".join(
            f"- {s.title} ({s.url})" for s in state.sources
        ) or "(no sources)"
        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Sources:\n{source_list}\n\n"
            f"Research notes:\n{state.research_notes}\n\n"
            f"Final answer:\n{state.final_answer}"
        )
        response = self._llm.complete(_SYSTEM_PROMPT, user_prompt)
        state.critique = response.content

        verdict = "REVISE" if "VERDICT: REVISE" in response.content.upper() else "PASS"
        state.add_trace_event(
            self.name, {"verdict": verdict, "cost_usd": response.cost_usd}
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=response.content,
                metadata={
                    "verdict": verdict,
                    "cost_usd": response.cost_usd,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        return state
