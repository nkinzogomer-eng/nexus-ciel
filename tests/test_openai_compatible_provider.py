import json

import pytest

from nexus.providers.openai_compatible import OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


@pytest.mark.asyncio
async def test_openai_compatible_provider_sends_request_and_accounts_usage(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse({
            "choices": [{"message": {"content": "verified output"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    monkeypatch.setattr("nexus.providers.openai_compatible.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:11434/v1",
        model="qwen-local",
        api_key="local-test-key",
        input_cost_per_1k_tokens=0.10,
        output_cost_per_1k_tokens=0.20,
        max_tokens=100,
    )
    from nexus.providers import CompletionRequest

    result = await provider.complete(CompletionRequest("hello"))

    assert captured["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert captured["payload"]["model"] == "qwen-local"
    assert captured["payload"]["messages"][0]["content"] == "hello"
    assert captured["timeout"] == 60.0
    assert result.text == "verified output"
    assert result.input_tokens == 10 and result.output_tokens == 5
    assert result.cost_usd == pytest.approx(0.002)
    assert result.confidence == 0.80


def test_openai_compatible_provider_estimates_full_input_and_output_budget():
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:11434/v1",
        model="local",
        input_cost_per_1k_tokens=0.10,
        output_cost_per_1k_tokens=0.20,
        max_tokens=100,
    )
    from nexus.providers import CompletionRequest

    estimate = provider.cost_estimate(CompletionRequest("a" * 400))
    assert estimate == pytest.approx((100 * 0.10 + 100 * 0.20) / 1000)


def test_provider_factory_does_not_silently_enable_synthetic_providers(monkeypatch):
    from nexus.providers.factory import build_providers_from_env

    monkeypatch.delenv("NEXUS_TEST_MODE", raising=False)
    for key in (
        "NEXUS_LLM_BASE_URL",
        "NEXUS_LLM_MODEL",
        "NEXUS_LLM_API_KEY",
        "NEXUS_LLM_COST_PER_1K_TOKENS",
        "NEXUS_LLM_INPUT_COST_PER_1K_TOKENS",
        "NEXUS_LLM_OUTPUT_COST_PER_1K_TOKENS",
    ):
        monkeypatch.delenv(key, raising=False)

    assert build_providers_from_env() == []


def test_hosted_provider_requires_explicit_token_prices(monkeypatch):
    from nexus.providers.factory import build_providers_from_env

    monkeypatch.delenv("NEXUS_TEST_MODE", raising=False)
    monkeypatch.setenv("NEXUS_LLM_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("NEXUS_LLM_MODEL", "example-model")
    monkeypatch.delenv("NEXUS_LLM_COST_PER_1K_TOKENS", raising=False)
    monkeypatch.delenv("NEXUS_LLM_INPUT_COST_PER_1K_TOKENS", raising=False)
    monkeypatch.delenv("NEXUS_LLM_OUTPUT_COST_PER_1K_TOKENS", raising=False)

    with pytest.raises(ValueError, match="require explicit input and output token prices"):
        build_providers_from_env()


def test_local_provider_factory_uses_explicitly_configured_endpoint(monkeypatch):
    from nexus.providers.factory import build_providers_from_env
    from nexus.providers.openai_compatible import OpenAICompatibleProvider

    monkeypatch.delenv("NEXUS_TEST_MODE", raising=False)
    monkeypatch.setenv("NEXUS_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("NEXUS_LLM_MODEL", "qwen-local")

    providers = build_providers_from_env()
    assert len(providers) == 1
    assert isinstance(providers[0], OpenAICompatibleProvider)
