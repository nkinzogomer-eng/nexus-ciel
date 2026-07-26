"""The routing policy is versioned data owned by the Evolution Engine.

The Router reads it and must never write it. These tests make that a
mechanical guarantee instead of a manual review step.
"""
import dataclasses
import json

import pytest

from nexus.providers import CompletionRequest, LocalProvider, SecondaryProvider
from nexus.router import (
    AdaptiveRouter,
    PolicyError,
    RoutingPolicy,
    load_policy,
    resolve_policy_path,
)
from nexus.router.policy import OFFICIAL_STAGES


def test_policy_file_exists_and_is_the_router_default():
    policy = load_policy()
    assert policy.source_path is not None
    assert policy.owner == "evolution_engine"
    assert policy.router_access == "read_only"
    assert policy.stages == OFFICIAL_STAGES


def test_router_default_policy_comes_from_the_versioned_file():
    router = AdaptiveRouter([LocalProvider()])
    on_disk = json.loads(resolve_policy_path().read_text(encoding="utf-8"))
    assert router.policy.confidence_threshold == on_disk["confidence_threshold"]
    assert list(router.policy.stages) == on_disk["stages"]
    assert router.policy.version == on_disk["policy_version"]


def test_policy_object_is_immutable():
    policy = load_policy()
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.confidence_threshold = 0.1  # type: ignore[misc]


@pytest.mark.asyncio
async def test_router_never_writes_the_policy_file():
    path = resolve_policy_path()
    before_bytes = path.read_bytes()
    before_mtime = path.stat().st_mtime_ns
    router = AdaptiveRouter([LocalProvider(confidence=0.20), SecondaryProvider(confidence=0.95)])
    await router.complete(CompletionRequest("write guard"))
    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime_ns == before_mtime


def test_policy_rejects_a_router_writable_file(tmp_path):
    bad = tmp_path / "routing_policy_v1.json"
    bad.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "policy_version": 1,
                "confidence_threshold": 0.75,
                "stages": list(OFFICIAL_STAGES),
                "owner": "evolution_engine",
                "router_access": "read_write",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PolicyError, match="router_access"):
        load_policy(bad)


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ({"confidence_threshold": 1.7}, "confidence_threshold"),
        ({"stages": ["large_model", "small_model"]}, "cascade order"),
        ({"stages": ["telepathy"]}, "official cascade"),
        ({"owner": "router"}, "owner"),
        ({"schema_version": 99}, "schema_version"),
    ],
)
def test_policy_rejects_malformed_files(tmp_path, mutation, expected):
    data = {
        "schema_version": 1,
        "policy_version": 1,
        "confidence_threshold": 0.75,
        "stages": list(OFFICIAL_STAGES),
        "owner": "evolution_engine",
        "router_access": "read_only",
    }
    data.update(mutation)
    bad = tmp_path / "policy.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PolicyError, match=expected):
        load_policy(bad)


def test_missing_policy_file_fails_loudly(tmp_path):
    with pytest.raises(PolicyError, match="not found"):
        load_policy(tmp_path / "nope.json")


def test_router_refuses_a_policy_it_could_write():
    writable = RoutingPolicy(router_access="read_write")
    with pytest.raises(PolicyError, match="read_only"):
        AdaptiveRouter([LocalProvider()], policy=writable)
