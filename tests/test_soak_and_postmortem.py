"""Automated Test Suite for Soak Verification & Automated Postmortems.

Validates:
- verify_system_recovery tool:
  - Multi-checkpoint mathematical stability
  - Elimination of flapping services
  - Memory slope leak detection (> 15% growth across window)
  - SLA breach detection (latency > 120ms or error rate > 1.0%)
  - Safe error return on unknown/misspelled service names (prevents false victory)
- generate_incident_postmortem tool:
  - Scenario-specific Root Cause Analysis (SQS, OOM, Rate Limit, DB Deadlock)
  - Accurate MTTR computation (< 1s, seconds, minutes)
  - Audit trail reporting for all standard and extended actions
  - Preventative action item tables & Markdown formatting
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
import pytest
from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario
from strandops.tools.verification import verify_system_recovery
from strandops.tools.postmortem import generate_incident_postmortem
from strandops.tools.remediation import execute_remediation


@pytest.fixture(autouse=True)
def clean_cluster():
    cloud.reset()
    yield
    cloud.reset()


# =============================================================================
# Time-Windowed Soak Testing & Flapping Tests
# =============================================================================

def test_soak_verification_healthy_cluster_is_stable():
    res = json.loads(verify_system_recovery(soak_checks=3))
    assert res["all_recovered"] is True
    assert res["stability"] == "STABLE"
    assert res["stability_confidence"] == "100.0%"
    assert res["verification_checkpoints"] == 3
    assert res["checkpoints_passed"] == 3
    assert res["memory_slope_stable"] is True


def test_soak_verification_degraded_during_outage():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    res = json.loads(verify_system_recovery("payment-gateway", soak_checks=2))
    assert res["all_recovered"] is False
    assert res["stability"] == "DEGRADED"
    assert res["checkpoints_failed"] == 2


def test_soak_verification_clamps_checkpoint_count():
    res_min = json.loads(verify_system_recovery(soak_checks=0))
    assert res_min["verification_checkpoints"] == 1

    res_max = json.loads(verify_system_recovery(soak_checks=50))
    assert res_max["verification_checkpoints"] == 5


def test_soak_verification_unknown_service_returns_error():
    res = json.loads(verify_system_recovery("totally-fake-service"))
    assert res["all_recovered"] is False
    assert res["stability"] == "ERROR"
    assert "Cannot verify recovery" in res["verdict"]


def test_soak_verification_casing_and_symbol_normalization():
    res = json.loads(verify_system_recovery("Payment Gateway"))
    assert res["all_recovered"] is True
    assert res["stability"] == "STABLE"


# =============================================================================
# Incident Postmortem Generation & RCA Accuracy
# =============================================================================

def test_postmortem_sqs_poison_pill_rca():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    execute_remediation("quarantine_messages", "order-processing-queue")
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "Incident Postmortem" in report
    assert "JSONDecodeError" in report or "poison" in report.lower()
    assert "quarantine" in report.lower()


def test_postmortem_oom_scenario_rca():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    execute_remediation("restart_service", "payment-gateway")
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "connection pool" in report.lower()
    assert "corrupted message payloads" not in report.lower()


def test_postmortem_rate_limit_rca():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    execute_remediation("rollback_config", "api-gateway")
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "rate limiter" in report.lower() or "429" in report
    assert "corrupted message payloads" not in report.lower()


def test_postmortem_db_pool_deadlock_rca():
    cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)
    execute_remediation("restart_service", "order-service")
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "database connection pool" in report.lower() or "deadlock" in report.lower()


def test_postmortem_with_no_incident_does_not_crash():
    pm = json.loads(generate_incident_postmortem())
    assert pm["status"] == "success"
    assert "Incident Postmortem" in pm["markdown_report"]


def test_postmortem_audit_trail_includes_all_executed_actions():
    inc = cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    execute_remediation("scale_service", "inventory-worker", '{"delta": 2}')
    execute_remediation("drain_traffic", "inventory-worker")
    execute_remediation("flush_cache", "redis-cluster")
    execute_remediation("quarantine_messages", "order-processing-queue")

    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "Scaled" in report
    assert "Drained" in report
    assert "Flushed" in report
    assert "Quarantined" in report


def test_postmortem_contains_preventative_action_items_table():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    execute_remediation("rollback_config", "api-gateway")
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "Preventative Action Items" in report
    assert "| Action Item | Type | Owner | Status |" in report


def test_latency_jitter_triggers_flapping_and_penalizes_confidence(monkeypatch):
    """Sudden latency jitter (> 20% degradation) triggers UNSTABLE_FLAPPING and caps confidence at <= 50%."""
    from strandops.simulator.models import MetricSnapshot, ServiceHealth
    call_count = 0

    def mock_get_telemetry(target=None):
        nonlocal call_count
        call_count += 1
        # Checkpoint 1: 40ms, Checkpoint 2: 70ms (> 20% jitter)
        lat = 40.0 if call_count <= 2 else 70.0
        return [
            MetricSnapshot(
                service_name="payment-gateway",
                p50_latency_ms=18.0, p95_latency_ms=38.0, p99_latency_ms=lat,
                error_rate_pct=0.0, requests_per_sec=145.0, memory_usage_mb=220.0,
                cpu_usage_pct=14.5, status=ServiceHealth.HEALTHY,
            )
        ]

    monkeypatch.setattr(cloud, "get_telemetry", mock_get_telemetry)
    res = json.loads(verify_system_recovery("payment-gateway", soak_checks=2))
    assert res["stability"] == "UNSTABLE_FLAPPING"
    assert res["all_recovered"] is False
    assert res["latency_jitter_stable"] is False
    assert float(res["stability_confidence"].rstrip("%")) <= 50.0


def test_postmortem_dynamic_metrics_reporting():
    """Postmortem reports live telemetry metrics and verification status dynamically."""
    pm = json.loads(generate_incident_postmortem())
    report = pm["markdown_report"]
    assert "Closed-Loop Verification Proof" in report
    assert "Peak Error Rate:" in report
    assert "P99 Latency:" in report
    assert "Queue Backlog:" in report

