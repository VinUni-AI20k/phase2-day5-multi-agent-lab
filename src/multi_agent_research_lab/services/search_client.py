"""Search client abstraction for ResearcherAgent."""

from __future__ import annotations

import logging

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client.

    Uses Tavily when ``TAVILY_API_KEY`` is set; otherwise falls back to a deterministic
    mock so the pipeline still runs end-to-end during the lab.
    """

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        settings = get_settings()
        if settings.tavily_api_key:
            return self._search_tavily(query, max_results, settings.tavily_api_key)
        logger.info("TAVILY_API_KEY not set; using mock search results.")
        return self._search_mock(query, max_results)

    def _search_mock(self, query: str, max_results: int) -> list[SourceDocument]:
        return [
            SourceDocument(
                title=f"Mock source {i + 1} for: {query[:40]}",
                url=f"https://example.com/doc/{i + 1}",
                snippet=f"Placeholder snippet {i + 1} discussing '{query}'.",
                metadata={"rank": i + 1, "provider": "mock"},
            )
            for i in range(max_results)
        ]

    def _search_tavily(
        self, query: str, max_results: int, api_key: str
    ) -> list[SourceDocument]:
        from tavily import TavilyClient  # pip install tavily-python

        results = TavilyClient(api_key=api_key).search(query, max_results=max_results)
        return [
            SourceDocument(
                title=item["title"],
                url=item["url"],
                snippet=item["content"],
                metadata={"score": item.get("score"), "provider": "tavily"},
            )
            for item in results["results"]
        ]
