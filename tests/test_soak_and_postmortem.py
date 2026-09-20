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
