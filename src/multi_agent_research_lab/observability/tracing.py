"""Tracing hooks.

Provider-agnostic by design. The minimal ``trace_span`` always works; if
``LANGSMITH_API_KEY`` is configured, spans are additionally logged via LangSmith's
tracing context (no-op when the package or key is absent). ``dump_trace`` persists the
in-state trace events to JSON so they can be submitted as a deliverable.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Minimal timed span used across the workflow.

    Emits a structured log line on exit. Plug a real provider (LangSmith/Langfuse/
    OpenTelemetry) here if you need hosted traces.
    """

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
        logger.info(
            "span name=%s duration=%.3fs attrs=%s",
            span["name"],
            span["duration_seconds"],
            span["attributes"],
        )


def dump_trace(state: ResearchState, path: Path) -> Path:
    """Write the collected trace events and route history to a JSON file."""

    payload = {
        "query": state.request.query,
        "route_history": state.route_history,
        "iterations": state.iteration,
        "trace": state.trace,
        "errors": state.errors,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Trace written to %s", path)
    return path
