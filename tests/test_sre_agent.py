"""Automated Test Suite for StrandsOps SRE Agent & Cloud Simulation.

Validates the full incident lifecycle:
- Chaos injection
- Telemetry & error log extraction
- Blast-radius safety gate evaluation
- Bounded remediation execution
- Closed-loop verification proof
- Postmortem generation
"""
from __future__ import annotations

import json
import os
import sys
import pytest

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario, ServiceHealth
from strandops.tools.telemetry import inspect_telemetry
from strandops.tools.diagnostics import fetch_error_logs, inspect_queue_health
from strandops.tools.safety import analyze_blast_radius
from strandops.tools.remediation import execute_remediation
from strandops.tools.verification import verify_system_recovery
from strandops.tools.postmortem import generate_incident_postmortem
from strandops.tools import SRE_TOOLS


@pytest.fixture(autouse=True)
def reset_cloud():
    """Ensure every test runs against a clean, baseline cloud state."""
    cloud.reset()
    yield
    cloud.reset()


# =============================================================================
# 1. Cloud Simulator & Baseline Telemetry Tests
# =============================================================================

def test_baseline_cloud_is_healthy():
    telemetry = cloud.get_telemetry()
    assert len(telemetry) == 4
    for t in telemetry:
        assert t.status == ServiceHealth.HEALTHY
        assert t.error_rate_pct == 0.0
        assert t.p99_latency_ms < 60.0


def test_sqs_poison_pill_chaos_injection():
    inc = cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    assert inc.severity.value == "SEV1"
    assert cloud.queue.dead_letter_count > 0
    assert len(cloud.queue.poison_pill_ids) == 3

    # Telemetry should reflect critical failure on inventory-worker
    telemetry = cloud.get_telemetry("inventory-worker")
    assert telemetry[0].status == ServiceHealth.CRITICAL
    assert telemetry[0].error_rate_pct > 80.0


def test_payment_gateway_oom_chaos_injection():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    telemetry = cloud.get_telemetry("payment-gateway")
    assert telemetry[0].status == ServiceHealth.CRITICAL
    assert telemetry[0].p99_latency_ms > 3000.0


def test_rate_limit_misconfig_chaos_injection():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    telemetry = cloud.get_telemetry("api-gateway")
    assert telemetry[0].status == ServiceHealth.CRITICAL
    assert telemetry[0].error_rate_pct > 80.0


# =============================================================================
# 2. Strands SRE Tool Functionality Tests
# =============================================================================

def test_inspect_telemetry_tool():
    # Direct tool invocation
    raw = inspect_telemetry(service_name="payment-gateway")
    data = json.loads(raw)
    assert data["services_inspected"] == 1
    assert data["telemetry"][0]["service"] == "payment-gateway"
    assert data["telemetry"][0]["sla_breached"] is False


def test_fetch_error_logs_tool():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    raw = fetch_error_logs(service_name="inventory-worker", limit=5)
    data = json.loads(raw)
    assert data["total_logs"] > 0
    assert any("JSONDecodeError" in str(e["error_type"]) for e in data["entries"])


def test_inspect_queue_health_tool():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    raw = inspect_queue_health("order-processing-queue")
    data = json.loads(raw)
    assert data["has_poison_pills"] is True
    assert data["health"] == "CRITICAL"
    assert len(data["poison_pill_ids"]) == 3


def test_analyze_blast_radius_tool():
    # Safety gate test on payment-gateway
    raw = analyze_blast_radius(proposed_action="restart_service", target_service="payment-gateway")
    data = json.loads(raw)
    assert data["safe_to_proceed"] is True
    assert data["risk_level"] == "MEDIUM"
    assert "order-service" in data["direct_dependents"]


# =============================================================================
# 3. End-to-End Remediation & Verification Cycle Tests
# =============================================================================

def test_full_poison_pill_remediation_lifecycle():
    # 1. Trigger outage
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)

    # 2. Verify queue is broken
    q_data = json.loads(inspect_queue_health("order-processing-queue"))
    assert q_data["has_poison_pills"] is True

    # 3. Safety check
    safety_data = json.loads(analyze_blast_radius("quarantine_messages", "order-processing-queue"))
    assert safety_data["safe_to_proceed"] is True

    # 4. Remediate
    rem_data = json.loads(execute_remediation("quarantine_messages", "order-processing-queue"))
    assert rem_data["result"]["status"] == "success"
    assert rem_data["result"]["quarantined_count"] == 3

    # 5. Closed-Loop Verification
    verify_data = json.loads(verify_system_recovery())
    assert verify_data["all_recovered"] is True
    assert "SUCCESS" in verify_data["verdict"]

    # 6. Postmortem generation
    pm_data = json.loads(generate_incident_postmortem())
    assert pm_data["status"] == "success"
    assert "Incident Postmortem" in pm_data["markdown_report"]
    assert "Mean Time to Resolve" in pm_data["markdown_report"]


def test_payment_gateway_restart_lifecycle():
    # 1. Trigger OOM
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)

    # 2. Remediate via container restart
    rem_data = json.loads(execute_remediation("restart_service", "payment-gateway"))
    assert rem_data["result"]["status"] == "success"

    # 3. Closed-Loop Verification
    verify_data = json.loads(verify_system_recovery("payment-gateway"))
    assert verify_data["all_recovered"] is True


def test_rate_limit_rollback_lifecycle():
    # 1. Trigger bad deploy
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)

    # 2. Roll back config
    rem_data = json.loads(execute_remediation("rollback_config", "api-gateway"))
    assert rem_data["result"]["status"] == "success"
    assert rem_data["result"]["active_version"] == "v1.8.2"

    # 3. Closed-Loop Verification
    verify_data = json.loads(verify_system_recovery("api-gateway"))
    assert verify_data["all_recovered"] is True


def test_db_connection_starvation_lifecycle():
    # 1. Trigger DB pool deadlock
    cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)

    # 2. Check telemetry shows degradation
    telemetry = cloud.get_telemetry("order-service")
    assert telemetry[0].status == ServiceHealth.CRITICAL

    # 3. Safety check
    safety = json.loads(analyze_blast_radius("restart_service", "order-service"))
    assert safety["safe_to_proceed"] is True

    # 4. Remediate by restarting order-service
    rem_data = json.loads(execute_remediation("restart_service", "order-service"))
    assert rem_data["result"]["status"] == "success"

    # 5. Verify closed-loop recovery
    verify_data = json.loads(verify_system_recovery("order-service"))
    assert verify_data["all_recovered"] is True


def test_sre_tools_registry():
    assert len(SRE_TOOLS) == 7
    for tool_fn in SRE_TOOLS:
        assert callable(tool_fn)


# =============================================================================
# 4. Safety Gate & Postmortem Enhancement Tests
# =============================================================================

def test_blast_radius_blocks_unknown_actions():
    """Unknown action types should be flagged HIGH risk and blocked."""
    raw = analyze_blast_radius(proposed_action="delete_database", target_service="order-service")
    data = json.loads(raw)
    assert data["risk_level"] == "HIGH"
    assert data["safe_to_proceed"] is False
    assert "Unknown action" in data["safety_rationale"][0]


def test_blast_radius_returns_metadata():
    """Safety gate should return dependent count and blast limit threshold."""
    raw = analyze_blast_radius(proposed_action="restart_service", target_service="payment-gateway")
    data = json.loads(raw)
    assert "dependent_count" in data
    assert "blast_limit_threshold" in data
    assert data["dependent_count"] == len(data["direct_dependents"])


def test_postmortem_oom_scenario_has_correct_rca():
    """Postmortem for OOM scenario should mention connection pool, not JSON payloads."""
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    cloud.restart_service_instance("payment-gateway")  # resolve it
    pm_data = json.loads(generate_incident_postmortem())
    report = pm_data["markdown_report"]
    assert "connection pool" in report.lower()
    assert "corrupted message payloads" not in report.lower()


def test_postmortem_rate_limit_scenario_has_correct_rca():
    """Postmortem for rate-limit scenario should mention deployment misconfiguration."""
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    cloud.rollback_service_config("api-gateway")  # resolve it
    pm_data = json.loads(generate_incident_postmortem())
    report = pm_data["markdown_report"]
    assert "rate limiter" in report.lower() or "429" in report
    assert "corrupted message payloads" not in report.lower()


# =============================================================================
# 5. Competitive Improvement Tests (Expanded Scope, Soak, Provider)
# =============================================================================

def test_scale_service_remediation():
    """Scale service should adjust instance count and return metadata."""
    raw = execute_remediation("scale_service", "inventory-worker", '{"delta": 3}')
    data = json.loads(raw)
    assert data["action_executed"] == "scale_service"
    assert data["result"]["status"] == "success"
    assert data["result"]["new_count"] == 5  # was 2, +3 = 5
    assert data["result"]["previous_count"] == 2


def test_scale_service_guardrail_clamps_delta():
    """Scale delta should be clamped to MAX_SCALE_DELTA (default 5)."""
    raw = execute_remediation("scale_service", "payment-gateway", '{"delta": 20}')
    data = json.loads(raw)
    assert data["result"]["status"] == "success"
    assert data["result"]["clamped"] is True
    assert data["result"]["delta_applied"] == 5  # clamped from 20 to 5
    assert data["result"]["new_count"] == 7  # was 2, +5 = 7


def test_drain_traffic_remediation():
    """Drain traffic should mark service as draining and identify upstream callers."""
    raw = execute_remediation("drain_traffic", "order-service")
    data = json.loads(raw)
    assert data["action_executed"] == "drain_traffic"
    assert data["result"]["status"] == "success"
    assert data["result"]["traffic_state"] == "draining"
    assert "api-gateway" in data["result"]["upstream_callers_notified"]


def test_drain_traffic_idempotent():
    """Draining an already-draining service should return already_draining status."""
    cloud.drain_service_traffic("payment-gateway")
    raw = execute_remediation("drain_traffic", "payment-gateway")
    data = json.loads(raw)
    assert data["result"]["status"] == "already_draining"


def test_soak_window_verification_stable():
    """Multi-checkpoint verification on a healthy cluster should report STABLE."""
    raw = verify_system_recovery(soak_checks=3)
    data = json.loads(raw)
    assert data["all_recovered"] is True
    assert data["stability"] == "STABLE"
    assert data["stability_confidence"] == "100.0%"
    assert data["verification_checkpoints"] == 3
    assert data["checkpoints_passed"] == 3


def test_soak_window_verification_degraded():
    """Multi-checkpoint verification during active incident should report DEGRADED."""
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    raw = verify_system_recovery(service_name="payment-gateway", soak_checks=2)
    data = json.loads(raw)
    assert data["all_recovered"] is False
    assert data["stability"] == "DEGRADED"
    assert data["checkpoints_failed"] == 2


def test_blast_radius_scale_action_is_low_risk():
    """Scaling actions should always be LOW risk since they don't interrupt traffic."""
    raw = analyze_blast_radius(proposed_action="scale_service", target_service="order-service")
    data = json.loads(raw)
    assert data["risk_level"] == "LOW"
    assert data["safe_to_proceed"] is True


def test_abstract_provider_interface():
    """CloudInfrastructure should be an instance of the abstract CloudProvider."""
    from strandops.simulator.provider import CloudProvider
    assert isinstance(cloud, CloudProvider)


def test_provider_factory_returns_singleton():
    """get_cloud_provider() must return the canonical singleton instance."""
    from strandops.simulator.provider import get_cloud_provider
    provider = get_cloud_provider()
    assert provider is cloud


def test_remediation_target_normalization():
    """Remediation must handle varied target naming formats (spaces, underscores, title case)."""
    for formatted_target in ["Payment Gateway", "payment_gateway", "Payment-Gateway"]:
        res_raw = execute_remediation("restart_service", formatted_target)
        res = json.loads(res_raw)
        assert res["result"]["status"] == "success"
        assert res["result"]["service"] == "payment-gateway"


def test_verification_nonexistent_service_returns_error():
    """Verifying a non-existent service must return error and not declare false success."""
    raw = verify_system_recovery(service_name="nonexistent-microservice")
    data = json.loads(raw)
    assert data["all_recovered"] is False
    assert data["stability"] == "ERROR"
    assert "Cannot verify recovery" in data["verdict"]


def test_safety_gate_target_normalization():
    """Safety gate must normalize names with spaces/underscores so order-service is flagged HIGH."""
    raw = analyze_blast_radius(proposed_action="restart_service", target_service="Order Service")
    data = json.loads(raw)
    assert data["risk_level"] == "HIGH"
    assert data["target"] == "order-service"


def test_scale_and_drain_recorded_in_incident_audit():
    """Scaling and draining operations must be recorded in the active incident audit trail."""
    inc = cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    execute_remediation("scale_service", "inventory-worker", '{"delta": 2}')
    execute_remediation("drain_traffic", "inventory-worker")
    actions = inc.remediation_actions_taken
    assert any("Scaled" in a for a in actions)
    assert any("Drained" in a for a in actions)


# =============================================================================
# 6. Pluggable SRE Runbook Registry & New Action Primitive Tests
# =============================================================================

def test_action_registry_contains_all_plugins():
    """Registry must have all 8 standard and extended plugins registered."""
    from strandops.plugins.registry import registry
    actions = registry.list_actions()
    names = [a["name"] for a in actions]
    expected = [
        "quarantine_messages", "restart_service", "rollback_config",
        "scale_service", "drain_traffic", "flush_cache",
        "trip_circuit_breaker", "reroute_traffic",
    ]
    for exp in expected:
        assert exp in names


def test_flush_cache_primitive():
    """flush_cache action should purge keys and record in incident audit."""
    res_raw = execute_remediation("flush_cache", "redis-cluster", '{"key_pattern": "session:*"}')
    res = json.loads(res_raw)
    assert res["action_executed"] == "flush_cache"
    assert res["result"]["status"] == "success"
    assert res["result"]["cache_cluster"] == "redis-cluster"
    assert res["result"]["key_pattern"] == "session:*"
    assert res["result"]["keys_cleared"] > 0


def test_trip_circuit_breaker_primitive():
    """trip_circuit_breaker action should set OPEN state and shed traffic."""
    res_raw = execute_remediation("trip_circuit_breaker", "payment-gateway", '{"shed_pct": 75}')
    res = json.loads(res_raw)
    assert res["action_executed"] == "trip_circuit_breaker"
    assert res["result"]["status"] == "success"
    assert res["result"]["circuit_breaker_state"] == "OPEN"
    assert res["result"]["traffic_shed_pct"] == 75


def test_reroute_traffic_primitive():
    """reroute_traffic action should shift traffic between Availability Zones."""
    res_raw = execute_remediation(
        "reroute_traffic", "api-gateway", '{"from_az": "us-east-1a", "to_az": "us-east-1b"}'
    )
    res = json.loads(res_raw)
    assert res["action_executed"] == "reroute_traffic"
    assert res["result"]["status"] == "success"
    assert res["result"]["from_az"] == "us-east-1a"
    assert res["result"]["to_az"] == "us-east-1b"


def test_safety_gate_evaluates_new_primitives():
    """Safety gate should recognize flush_cache as LOW and reroute_traffic as HIGH risk."""
    flush_gate = json.loads(analyze_blast_radius("flush_cache", "redis-cluster"))
    assert flush_gate["risk_level"] == "LOW"
    assert flush_gate["safe_to_proceed"] is True

    reroute_gate = json.loads(analyze_blast_radius("reroute_traffic", "api-gateway"))
    assert reroute_gate["risk_level"] == "HIGH"


# =============================================================================
# 7. Semantic Incident Cache & Fast Triage Tests
# =============================================================================

def test_semantic_cache_instant_hit():
    """Known failure signature should yield sub-millisecond zero-cost cache hit."""
    from strandops.cache import incident_cache
    hit = incident_cache.lookup(
        service="inventory-worker",
        error_type="json.decoder.JSONDecodeError",
        signature="Unterminated string starting at line",
    )
    assert hit is not None
    assert hit["cache_hit"] is True
    assert hit["estimated_cost_usd"] == 0.0
    assert hit["remediation_plan"]["action_type"] == "quarantine_messages"


def test_semantic_cache_miss_escalates():
    """Unknown failure signature should register as a cache miss."""
    from strandops.cache import incident_cache
    miss = incident_cache.lookup(
        service="unknown-service",
        error_type="CustomNovelError",
        signature="Something totally unheard of",
    )
    assert miss is None


def test_fast_triage_incident_routing():
    """fast_triage_incident routes known incidents to Tier-0 cache and novel ones to Tier-2."""
    from strandops.agent import fast_triage_incident
    # Known pattern
    triage_hit = fast_triage_incident(
        service_name="payment-gateway",
        error_type="ConnectionPoolTimeout",
        signature="Connection pool is full, discarding connection",
    )
    assert triage_hit["tier"] == "Tier-0 (Semantic Cache Hit)"
    assert triage_hit["escalation_needed"] is False
    assert triage_hit["plan"]["action_type"] == "restart_service"

    # Novel pattern
    triage_miss = fast_triage_incident(
        service_name="payment-gateway",
        error_type="UnexpectedVendorKafkaDrop",
        signature="Fatal protocol handshake mismatch",
    )
    assert triage_miss["tier"] == "Tier-1 (Fast Triage)"
    assert triage_miss["escalation_needed"] is True
    assert triage_miss["escalate_to"] == "Tier-2 (Claude 3.5 Sonnet)"


# =============================================================================
# 8. Time-Windowed Soak Testing & Mathematical Stability Tests
# =============================================================================

def test_soak_window_verification_with_window_parameter():
    """verify_system_recovery supports soak_window_seconds and reports stability metrics."""
    raw = verify_system_recovery(soak_checks=2, soak_window_seconds=1)
    data = json.loads(raw)
    assert data["all_recovered"] is True
    assert data["stability"] == "STABLE"
    assert data["memory_slope_stable"] is True
    assert data["verification_checkpoints"] == 2


# =============================================================================
# 9. Live AWS Provider Adapter Tests
# =============================================================================

def test_live_aws_provider_structure():
    """LiveAWSProvider should implement all CloudProvider abstract methods."""
    from strandops.simulator.aws_provider import LiveAWSProvider
    from strandops.simulator.provider import CloudProvider

    aws_provider = LiveAWSProvider(region_name="us-east-1")
    assert isinstance(aws_provider, CloudProvider)
    assert aws_provider.region == "us-east-1"
    telemetry = aws_provider.get_telemetry("payment-gateway")
    assert len(telemetry) == 1
    assert telemetry[0].service_name == "payment-gateway"
    assert telemetry[0].p99_latency_ms > 0

