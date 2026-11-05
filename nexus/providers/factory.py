from __future__ import annotations

import os
from urllib.parse import urlsplit

from .base import ProviderAdapter
from .local import LocalProvider
from .openai_compatible import OpenAICompatibleProvider
from .secondary import SecondaryProvider


def build_providers_from_env() -> list[ProviderAdapter]:
    """Build configured production providers; synthetic providers are test-only."""
    if os.getenv("NEXUS_TEST_MODE", "").lower() in {"1", "true", "yes"}:
        return [LocalProvider(), SecondaryProvider()]

    base_url = os.getenv("NEXUS_LLM_BASE_URL")
    model = os.getenv("NEXUS_LLM_MODEL")
    if not base_url and not model:
        return []
    if not base_url or not model:
        raise ValueError("NEXUS_LLM_BASE_URL and NEXUS_LLM_MODEL must be configured together")

    host = (urlsplit(base_url).hostname or "").lower()
    is_local = host in {"localhost", "127.0.0.1", "::1"}
    shared_rate = os.getenv("NEXUS_LLM_COST_PER_1K_TOKENS")
    input_rate = os.getenv("NEXUS_LLM_INPUT_COST_PER_1K_TOKENS") or shared_rate
    output_rate = os.getenv("NEXUS_LLM_OUTPUT_COST_PER_1K_TOKENS") or shared_rate
    if not is_local and (input_rate is None or output_rate is None):
        raise ValueError(
            "hosted providers require explicit input and output token prices; "
            "set NEXUS_LLM_COST_PER_1K_TOKENS or both directional price variables"
        )

    return [
        OpenAICompatibleProvider(
            base_url=base_url,
            model=model,
            api_key=os.getenv("NEXUS_LLM_API_KEY"),
            stage=os.getenv("NEXUS_LLM_STAGE", "large_model"),
            timeout_s=float(os.getenv("NEXUS_LLM_TIMEOUT_S", "60")),
            max_tokens=int(os.getenv("NEXUS_LLM_MAX_TOKENS", "2048")),
            input_cost_per_1k_tokens=float(input_rate or 0.0),
            output_cost_per_1k_tokens=float(output_rate or 0.0),
            routing_confidence=float(os.getenv("NEXUS_LLM_ROUTING_CONFIDENCE", "0.80")),
        )
    ]
