"""Search client abstraction for ResearcherAgent."""

import logging

from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client.

    Uses Tavily when TAVILY_API_KEY is set, otherwise falls back to a mock.
    """

    def __init__(self) -> None:
        from multi_agent_research_lab.core.config import get_settings
        settings = get_settings()
        self._tavily_key = settings.tavily_api_key

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        if self._tavily_key:
            return self._tavily_search(query, max_results)
        logger.info("No TAVILY_API_KEY — using mock search for: %s", query)
        return self._mock_search(query, max_results)

    def _tavily_search(self, query: str, max_results: int) -> list[SourceDocument]:
        from tavily import TavilyClient  # type: ignore[import]
        client = TavilyClient(api_key=self._tavily_key)
        results = client.search(query=query, max_results=max_results)
        return [
            SourceDocument(
                title=r.get("title", "Untitled"),
                url=r.get("url"),
                snippet=r.get("content", ""),
            )
            for r in results.get("results", [])
        ]

    def _mock_search(self, query: str, max_results: int) -> list[SourceDocument]:
        keywords = query.lower().split()[:4]
        topic = " ".join(keywords[:2])
        docs = [
            SourceDocument(
                title=f"Overview of {topic} — Survey 2024",
                url=f"https://arxiv.org/abs/mock-{hash(query) % 9999:04d}",
                snippet=(
                    f"This survey covers the state-of-the-art approaches in {topic}. "
                    "We review key methods, benchmarks, and open challenges, "
                    "with a focus on practical deployment in production systems."
                ),
            ),
            SourceDocument(
                title=f"{topic.title()}: A Practical Guide",
                url=f"https://docs.example.com/{topic.replace(' ', '-')}",
                snippet=(
                    f"A practitioner's introduction to {topic}. "
                    "Covers architecture patterns, failure modes, and recommended guardrails "
                    "for large-scale deployments."
                ),
            ),
            SourceDocument(
                title=f"Benchmarking {topic.title()} Systems",
                url=f"https://blog.research.example.com/{hash(topic) % 999}",
                snippet=(
                    f"Empirical evaluation of {topic} systems across latency, throughput, "
                    "and quality metrics. Results show that multi-step pipelines outperform "
                    "single-step baselines by 15-30% on complex queries."
                ),
            ),
            SourceDocument(
                title=f"Production Lessons: {topic.title()}",
                url=f"https://engineering.example.com/lessons-{hash(query) % 888}",
                snippet=(
                    f"Lessons learned running {topic} in production. "
                    "Key takeaways: guard against hallucinations with grounding, "
                    "implement structured output validation, and monitor agent loops."
                ),
            ),
            SourceDocument(
                title=f"Failure Modes in {topic.title()} Pipelines",
                url=f"https://papers.example.com/{hash(query) % 777}",
                snippet=(
                    f"Analysis of common failure modes in {topic} pipelines: "
                    "infinite loops, context overflow, tool call errors, and cascading failures. "
                    "Mitigation strategies include max_iterations, timeouts, and circuit breakers."
                ),
            ),
        ]
        return docs[:max_results]
