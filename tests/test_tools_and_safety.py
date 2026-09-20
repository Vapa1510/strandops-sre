"""Automated Test Suite for SRE Tools & Safety Gate.

Validates:
- inspect_telemetry tool (single service, all services, SLA breach flag, unknown service)
- fetch_error_logs tool (limit clamping, service filtering, severity inspection)
- inspect_queue_health tool (visible depth, DLQ count, poison pill IDs, case insensitivity)
- analyze_blast_radius safety gate (low, medium, high risk classification, auto-approval vs human gate)
- Safety gate evaluation for all 8 action primitives
- Error handling for unrecognized actions and malformed parameters
"""
from __future__ import annotations

import json
import pytest
from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario
from strandops.tools.telemetry import inspect_telemetry
from strandops.tools.diagnostics import fetch_error_logs, inspect_queue_health
from strandops.tools.safety import analyze_blast_radius
from strandops.tools.remediation import execute_remediation


@pytest.fixture(autouse=True)
def clean_cluster():
    cloud.reset()
    yield
    cloud.reset()


# =============================================================================
# Telemetry Tool Tests
# =============================================================================

def test_inspect_telemetry_all_services():
    res = json.loads(inspect_telemetry())
    assert res["services_inspected"] == 4
    for t in res["telemetry"]:
        assert "p99_latency_ms" in t
        assert "error_rate_pct" in t
        assert t["sla_breached"] is False


def test_inspect_telemetry_single_service():
    res = json.loads(inspect_telemetry("payment-gateway"))
    assert res["services_inspected"] == 1
    assert res["telemetry"][0]["service"] == "payment-gateway"


def test_inspect_telemetry_detects_sla_breach():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    res = json.loads(inspect_telemetry("api-gateway"))
    assert res["telemetry"][0]["sla_breached"] is True


def test_inspect_telemetry_unknown_service_returns_error():
    res = json.loads(inspect_telemetry("nonexistent-microservice"))
    assert res["status"] == "error"
    assert "not found" in res["message"]


def test_inspect_telemetry_casing_and_hyphen_normalization():
    for target in ["Order Service", "order_service", "ORDER-SERVICE"]:
        res = json.loads(inspect_telemetry(target))
        assert res["services_inspected"] == 1
        assert res["telemetry"][0]["service"] == "order-service"


# =============================================================================
# Diagnostics & Queue Health Tool Tests
# =============================================================================

def test_fetch_error_logs_all_services():
    # Healthy baseline only emits INFO — inject chaos so WARN/ERROR exist
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    res = json.loads(fetch_error_logs())
    assert res["total_logs"] > 0
    assert res["filter_service"] == "ALL"
    assert all(e["level"] in ("WARN", "ERROR", "FATAL") for e in res["entries"])


def test_fetch_error_logs_clamps_limit():
    # Below min (0 -> clamped to 1)
    res_min = json.loads(fetch_error_logs(limit=0))
    assert len(res_min["entries"]) <= 1

    # Above max (500 -> clamped to 50)
    res_max = json.loads(fetch_error_logs(limit=500))
    assert len(res_max["entries"]) <= 50


def test_fetch_error_logs_service_filtering():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    res = json.loads(fetch_error_logs(service_name="payment-gateway", limit=10))
    for entry in res["entries"]:
        assert entry["service"] == "payment-gateway"


def test_fetch_error_logs_casing_normalization():
    res = json.loads(fetch_error_logs(service_name="Inventory_Worker", limit=5))
    assert res["total_logs"] >= 0


def test_inspect_queue_health_baseline():
    res = json.loads(inspect_queue_health("order-processing-queue"))
    assert res["queue_name"] == "order-processing-queue"
    assert res["health"] == "HEALTHY"
    assert res["has_poison_pills"] is False
    assert res["dead_letter_count"] == 0


def test_inspect_queue_health_under_poison_storm():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    res = json.loads(inspect_queue_health("order-processing-queue"))
    assert res["health"] == "CRITICAL"
    assert res["has_poison_pills"] is True
    assert len(res["poison_pill_ids"]) == 3
    assert res["dead_letter_count"] > 0


def test_inspect_queue_health_unknown_queue():
    res = json.loads(inspect_queue_health("invalid-queue-name"))
    assert res["status"] == "error"
    assert "not found" in res["message"]


def test_inspect_queue_health_case_and_symbol_normalization():
    res = json.loads(inspect_queue_health("Order_Processing_Queue"))
    assert res["queue_name"] == "order-processing-queue"


# =============================================================================
# Blast Radius & Safety Gate Tests
# =============================================================================

def test_blast_radius_quarantine_is_low_risk():
    res = json.loads(analyze_blast_radius("quarantine_messages", "order-processing-queue"))
    assert res["risk_level"] == "LOW"
    assert res["safe_to_proceed"] is True


def test_blast_radius_restart_leaf_service_is_medium_risk():
    res = json.loads(analyze_blast_radius("restart_service", "payment-gateway"))
    assert res["risk_level"] == "MEDIUM"
    assert res["safe_to_proceed"] is True
    assert "order-service" in res["direct_dependents"]


def test_blast_radius_restart_core_service_is_high_risk():
    res = json.loads(analyze_blast_radius("restart_service", "order-service"))
    assert res["risk_level"] == "HIGH"
    assert res["dependent_count"] == 1  # api-gateway
    assert res["safe_to_proceed"] is True  # within default limit of 2


def test_blast_radius_blocks_when_dependents_exceed_limit(monkeypatch):
    monkeypatch.setenv("AUTO_REMEDIATE_BLAST_LIMIT", "0")
    res = json.loads(analyze_blast_radius("restart_service", "order-service"))
    assert res["risk_level"] == "HIGH"
    assert res["safe_to_proceed"] is False
    assert any("BLOCKED" in r for r in res["safety_rationale"])


def test_blast_radius_rollback_config_is_low_risk():
    res = json.loads(analyze_blast_radius("rollback_config", "api-gateway"))
    assert res["risk_level"] == "LOW"
    assert res["safe_to_proceed"] is True


def test_blast_radius_scale_service_is_low_risk():
    res = json.loads(analyze_blast_radius("scale_service", "inventory-worker"))
    assert res["risk_level"] == "LOW"
    assert res["safe_to_proceed"] is True


def test_blast_radius_drain_traffic_is_medium_risk():
    res = json.loads(analyze_blast_radius("drain_traffic", "order-service"))
    assert res["risk_level"] == "MEDIUM"


def test_blast_radius_flush_cache_is_low_risk():
    res = json.loads(analyze_blast_radius("flush_cache", "redis-cluster"))
    assert res["risk_level"] == "LOW"
    assert res["safe_to_proceed"] is True


def test_blast_radius_circuit_breaker_is_medium_risk():
    res = json.loads(analyze_blast_radius("trip_circuit_breaker", "payment-gateway"))
    assert res["risk_level"] == "MEDIUM"


def test_blast_radius_reroute_traffic_is_high_risk():
    res = json.loads(analyze_blast_radius("reroute_traffic", "api-gateway"))
    assert res["risk_level"] == "HIGH"


def test_blast_radius_unknown_action_is_blocked():
    res = json.loads(analyze_blast_radius("drop_database_tables", "order-service"))
    assert res["risk_level"] == "HIGH"
    assert res["safe_to_proceed"] is False
    assert any("Unknown action" in r for r in res["safety_rationale"])


def test_blast_radius_handles_empty_inputs():
    res = json.loads(analyze_blast_radius("", ""))
    assert res["risk_level"] == "HIGH"
    assert res["safe_to_proceed"] is False
