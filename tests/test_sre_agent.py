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
