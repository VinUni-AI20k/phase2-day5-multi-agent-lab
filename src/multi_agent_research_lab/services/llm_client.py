"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
Retry, timeout, and token logging live here rather than inside agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)

# Reference pricing for gpt-4o-mini (USD per token). Update if you change the model.
_PRICE_IN_PER_TOKEN = 0.15 / 1_000_000
_PRICE_OUT_PER_TOKEN = 0.60 / 1_000_000


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client backed by OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in your .env file."
            )
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.timeout_seconds,
        )
        self._model = settings.openai_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with token usage and estimated cost."""

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        cost = (input_tokens or 0) * _PRICE_IN_PER_TOKEN + (
            output_tokens or 0
        ) * _PRICE_OUT_PER_TOKEN

        logger.info(
            "LLM call model=%s in_tokens=%s out_tokens=%s cost_usd=%.6f",
            self._model,
            input_tokens,
            output_tokens,
            cost,
        )

        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
