from __future__ import annotations

import asyncio
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .base import CompletionRequest, CompletionResult, ProviderCaps, ProviderHealth


class OpenAICompatibleProvider:
    """Real chat-completions adapter for OpenAI-compatible local or hosted APIs.

    The configured routing_confidence is a routing hint, not a correctness
    probability. Mission success still requires an independent verifier.
    """

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        stage: str = "large_model",
        timeout_s: float = 60.0,
        max_tokens: int = 2048,
        input_cost_per_1k_tokens: float = 0.0,
        output_cost_per_1k_tokens: float = 0.0,
        routing_confidence: float = 0.80,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if not model.strip():
            raise ValueError("model must not be empty")
        if stage not in {"small_model", "large_model", "deep"}:
            raise ValueError(f"unsupported provider stage: {stage}")
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("timeout_s must be finite and positive")
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if any(not math.isfinite(x) or x < 0 for x in (input_cost_per_1k_tokens, output_cost_per_1k_tokens)):
            raise ValueError("token prices must be finite and non-negative")
        if not math.isfinite(routing_confidence) or not 0 <= routing_confidence <= 1:
            raise ValueError("routing_confidence must be between 0 and 1")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.stage = stage
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self.input_cost_per_1k_tokens = input_cost_per_1k_tokens
        self.output_cost_per_1k_tokens = output_cost_per_1k_tokens
        self.routing_confidence = routing_confidence

    async def health(self) -> ProviderHealth:
        # Avoid a hidden network request during health checks. Actual transport
        # failures are surfaced by complete() and handled by the router cascade.
        return ProviderHealth(True, f"configured endpoint for model {self.model}")

    def capabilities(self) -> ProviderCaps:
        return ProviderCaps(context_window=0, tools=False, json_mode=True)

    def cost_estimate(self, request: CompletionRequest) -> float:
        estimated_input_tokens = max(1, math.ceil(len(request.prompt) / 4))
        return (
            estimated_input_tokens * self.input_cost_per_1k_tokens
            + self.max_tokens * self.output_cost_per_1k_tokens
        ) / 1000.0

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return await asyncio.to_thread(self._complete_sync, request)

    def _complete_sync(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": self.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        http_request = Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(http_request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise RuntimeError(f"provider HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"provider transport failure: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("provider response has no choices[0].message.content") from exc
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise RuntimeError("provider response content is not text")

        usage = body.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or math.ceil(len(request.prompt) / 4))
        output_tokens = int(usage.get("completion_tokens") or math.ceil(len(content) / 4))
        cost = (
            input_tokens * self.input_cost_per_1k_tokens
            + output_tokens * self.output_cost_per_1k_tokens
        ) / 1000.0
        return CompletionResult(
            text=content,
            confidence=self.routing_confidence,
            cost_usd=cost,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
