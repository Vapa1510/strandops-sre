"""Automated Test Suite for Cloud Provider Interface & Live AWS Adapter.

Validates:
- Abstract CloudProvider base class contract
- CloudInfrastructure and LiveAWSProvider inheritance compliance
- get_cloud_provider() factory singleton caching
- Environment toggle (CLOUD_BACKEND=simulator vs CLOUD_BACKEND=aws)
- LiveAWSProvider method signatures and fallback resilience
"""
from __future__ import annotations

import os
import pytest
from strandops.simulator.provider import CloudProvider, get_cloud_provider
from strandops.simulator.cloud import cloud, CloudInfrastructure
from strandops.simulator.aws_provider import LiveAWSProvider


def test_cloud_infrastructure_is_cloud_provider():
    assert isinstance(cloud, CloudProvider)
    assert isinstance(cloud, CloudInfrastructure)


def test_get_cloud_provider_returns_simulator_singleton_by_default():
    provider = get_cloud_provider()
    assert provider is cloud


def test_live_aws_provider_is_cloud_provider():
    aws_provider = LiveAWSProvider(region_name="eu-west-1")
    assert isinstance(aws_provider, CloudProvider)
    assert aws_provider.region == "eu-west-1"


def test_live_aws_provider_implements_all_required_methods():
    aws_provider = LiveAWSProvider(region_name="us-east-1")
    required_methods = [
        "reset",
        "get_telemetry",
        "get_logs",
        "get_queue_state",
        "get_topology",
        "quarantine_queue_messages",
        "restart_service_instance",
        "rollback_service_config",
        "scale_service_instances",
        "drain_service_traffic",
        "flush_cache",
        "trip_circuit_breaker",
        "reroute_traffic",
    ]
    for method_name in required_methods:
        assert hasattr(aws_provider, method_name)
        assert callable(getattr(aws_provider, method_name))


def test_live_aws_provider_telemetry_output_contract():
    aws_provider = LiveAWSProvider(region_name="us-east-1")
    telemetry = aws_provider.get_telemetry("payment-gateway")
    assert len(telemetry) == 1
    t = telemetry[0]
    assert t.service_name == "payment-gateway"
    assert t.p99_latency_ms > 0
    assert t.memory_usage_mb > 0
    assert t.status is not None


def test_live_aws_provider_queue_state_contract():
    aws_provider = LiveAWSProvider(region_name="us-east-1")
    q = aws_provider.get_queue_state()
    assert q.queue_name == "order-processing-queue"
    assert q.dead_letter_queue_name == "order-processing-dlq"


def test_live_aws_provider_remediation_primitives_contract():
    aws_provider = LiveAWSProvider(region_name="us-east-1")

    # Restart
    res_restart = aws_provider.restart_service_instance("order-service")
    assert res_restart["status"] == "success"
    assert res_restart["provider"] == "aws"

    # Scale
    res_scale = aws_provider.scale_service_instances("inventory-worker", delta=2)
    assert res_scale["status"] == "success"
    assert res_scale["delta_applied"] == 2

    # Drain
    res_drain = aws_provider.drain_service_traffic("payment-gateway")
    assert res_drain["status"] == "success"

    # Flush cache
    res_flush = aws_provider.flush_cache("redis-cluster", key_pattern="*")
    assert res_flush["status"] == "success"

    # Trip circuit breaker
    res_trip = aws_provider.trip_circuit_breaker("payment-gateway", shed_pct=80)
    assert res_trip["status"] == "success"
    assert res_trip["traffic_shed_pct"] == 80

    # Reroute AZ traffic
    res_reroute = aws_provider.reroute_traffic("api-gateway", from_az="us-east-1a", to_az="us-east-1b")
    assert res_reroute["status"] == "success"


def test_cloud_backend_toggle_instantiates_aws_provider(monkeypatch):
    from strandops.simulator import provider as prov_module
    # Clear singleton cache
    monkeypatch.setattr(prov_module, "_provider_instance", None)
    monkeypatch.setenv("CLOUD_BACKEND", "aws")

    provider = prov_module.get_cloud_provider()
    assert isinstance(provider, LiveAWSProvider)

    # Restore singleton cache
    monkeypatch.setattr(prov_module, "_provider_instance", cloud)
