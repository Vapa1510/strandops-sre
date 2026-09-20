"""Automated Test Suite for Pluggable SRE Runbook Registry & Action Plugins.

Validates:
- ActionRegistry discovery, registration, and dispatch
- QuarantineMessagesPlugin (DLQ isolation & poison pill resolution)
- RestartServicePlugin (OOM and pool deadlock clearance)
- RollbackConfigPlugin (deployment revert & rate-limit restoration)
- ScaleServicePlugin (guardrails: delta clamping, min 1, max 10 bounds)
- DrainTrafficPlugin (graceful draining, idempotency, upstream notification)
- FlushCachePlugin (Redis key purging and pattern support)
- TripCircuitBreakerPlugin (traffic shedding % and OPEN/CLOSED state)
- RerouteTrafficPlugin (Availability Zone traffic shifting)
- Custom user-defined RemediationPlugin extension
"""
from __future__ import annotations

import json
import pytest
from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario
from strandops.plugins.base import RemediationPlugin
from strandops.plugins.registry import ActionRegistry, registry
from strandops.tools.remediation import execute_remediation


@pytest.fixture(autouse=True)
def clean_cluster():
    cloud.reset()
    yield
    cloud.reset()


# =============================================================================
# Action Registry Core Tests
# =============================================================================

def test_registry_has_all_eight_default_plugins():
    names = [a["name"] for a in registry.list_actions()]
    assert len(names) == 8
    expected = [
        "quarantine_messages", "restart_service", "rollback_config",
        "scale_service", "drain_traffic", "flush_cache",
        "trip_circuit_breaker", "reroute_traffic"
    ]
    for exp in expected:
        assert exp in names


def test_registry_get_case_insensitive_and_symbol_tolerant():
    assert registry.get("scale_service") is not None
    assert registry.get("SCALE_SERVICE") is not None
    assert registry.get("scale-service") is not None
    assert registry.get("restart_service") is not None


def test_registry_get_unknown_action_returns_none():
    assert registry.get("nonexistent_action") is None


def test_registry_custom_plugin_registration():
    class CustomMaintenancePlugin(RemediationPlugin):
        action_name: str = "custom_maintenance"
        description: str = "Test custom maintenance task"
        risk_level: str = "LOW"

        def execute(self, cloud, target, parameters):
            return {"status": "success", "custom_field": "ok"}

    reg = ActionRegistry()
    reg.register(CustomMaintenancePlugin())
    plugin = reg.get("custom_maintenance")
    assert plugin is not None
    assert plugin.action_name == "custom_maintenance"
    res = reg.execute(cloud, "custom_maintenance", "api-gateway", {})
    assert res["status"] == "success"


# =============================================================================
# Standard Remediation Primitives Execution
# =============================================================================

def test_quarantine_messages_resolves_poison_pills():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    res_raw = execute_remediation("quarantine_messages", "order-processing-queue")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["quarantined_count"] == 3
    assert len(cloud.queue.poison_pill_ids) == 0
    assert cloud.active_incident.status == "RESOLVED"


def test_restart_service_clears_payment_gateway_oom():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    res_raw = execute_remediation("restart_service", "payment-gateway")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert cloud.active_chaos is None
    assert cloud.active_incident.status == "RESOLVED"


def test_restart_service_clears_db_pool_deadlock():
    cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)
    res_raw = execute_remediation("restart_service", "order-service")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert cloud.active_chaos is None


def test_rollback_config_restores_api_gateway():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    res_raw = execute_remediation("rollback_config", "api-gateway")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["active_version"] == "v1.8.2"
    assert cloud.service_configs["api-gateway"]["rate_limit_rps"] == 500


# =============================================================================
# Scaling Guardrail Tests
# =============================================================================

def test_scale_service_up():
    res_raw = execute_remediation("scale_service", "inventory-worker", '{"delta": 3}')
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["new_count"] == 5  # was 2, +3 = 5


def test_scale_service_down():
    cloud.instance_counts["order-service"] = 5
    res_raw = execute_remediation("scale_service", "order-service", '{"delta": -2}')
    res = json.loads(res_raw)
    assert res["result"]["new_count"] == 3


def test_scale_service_clamps_delta_to_max_five():
    res_raw = execute_remediation("scale_service", "payment-gateway", '{"delta": 50}')
    res = json.loads(res_raw)
    assert res["result"]["clamped"] is True
    assert res["result"]["delta_applied"] == 5
    assert res["result"]["new_count"] == 7  # 2 + 5


def test_scale_service_never_scales_below_one():
    res_raw = execute_remediation("scale_service", "api-gateway", '{"delta": -10}')
    res = json.loads(res_raw)
    assert res["result"]["new_count"] == 1  # clamped to min 1


def test_scale_service_never_scales_above_ten():
    cloud.instance_counts["payment-gateway"] = 8
    res_raw = execute_remediation("scale_service", "payment-gateway", '{"delta": 5}')
    res = json.loads(res_raw)
    assert res["result"]["new_count"] == 10  # clamped to max 10


# =============================================================================
# Advanced Operational Primitives: Drain, Cache, Circuit Breaker, AZ Reroute
# =============================================================================

def test_drain_traffic_notifies_upstream_callers():
    res_raw = execute_remediation("drain_traffic", "order-service")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert "api-gateway" in res["result"]["upstream_callers_notified"]
    assert "order-service" in cloud.draining_services


def test_drain_traffic_is_idempotent():
    execute_remediation("drain_traffic", "payment-gateway")
    res_raw = execute_remediation("drain_traffic", "payment-gateway")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "already_draining"


def test_flush_cache_default_pattern():
    res_raw = execute_remediation("flush_cache", "redis-cluster")
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["keys_cleared"] > 1000


def test_flush_cache_custom_pattern():
    res_raw = execute_remediation("flush_cache", "catalog-cache", '{"key_pattern": "catalog:v2:*"}')
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["key_pattern"] == "catalog:v2:*"


def test_trip_circuit_breaker_partial_shed():
    res_raw = execute_remediation("trip_circuit_breaker", "payment-gateway", '{"shed_pct": 50}')
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["circuit_breaker_state"] == "OPEN"
    assert res["result"]["traffic_shed_pct"] == 50


def test_trip_circuit_breaker_full_shed():
    res_raw = execute_remediation("trip_circuit_breaker", "payment-gateway", '{"shed_pct": 100}')
    res = json.loads(res_raw)
    assert res["result"]["circuit_breaker_state"] == "OPEN"
    assert res["result"]["traffic_shed_pct"] == 100


def test_reroute_traffic_between_availability_zones():
    res_raw = execute_remediation(
        "reroute_traffic", "api-gateway", '{"from_az": "us-east-1a", "to_az": "us-east-1c"}'
    )
    res = json.loads(res_raw)
    assert res["result"]["status"] == "success"
    assert res["result"]["from_az"] == "us-east-1a"
    assert res["result"]["to_az"] == "us-east-1c"


def test_action_aliases_resolve_correctly():
    # 'scale_up' alias maps to 'scale_service'
    res_raw = execute_remediation("scale_up", "inventory-worker", '{"delta": 1}')
    res = json.loads(res_raw)
    assert res["action_executed"] == "scale_service"

    # 'reboot_instance' alias maps to 'restart_service'
    res_reboot = execute_remediation("reboot_instance", "payment-gateway")
    assert json.loads(res_reboot)["action_executed"] == "restart_service"
