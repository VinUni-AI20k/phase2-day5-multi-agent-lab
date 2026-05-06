"""Tests for the search client mock fallback."""

import pytest

from multi_agent_research_lab.services.search_client import SearchClient


def test_mock_search_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = SearchClient()
    docs = client.search("multi-agent systems for production", max_results=3)
    assert len(docs) == 3
    for d in docs:
        assert d.title
        assert d.snippet
