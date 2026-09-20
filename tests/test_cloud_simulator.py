"""Automated Test Suite for Cloud Simulator & Chaos Engine.

Validates:
- Baseline healthy state invariants (latencies, error rates, RPS, memory)
- Microservice instance counts & default configurations
- SQS queue and Dead-Letter Queue initial states
- In-memory structured log ring buffer
- Chaos Scenario 1: SQS Poison Pill Storm
- Chaos Scenario 2: Payment Gateway Memory Leak (OOM)
- Chaos Scenario 3: Bad Rate-Limit Deployment (HTTP 429)
- Chaos Scenario 4: DB Connection Pool Starvation
- Cluster reset restoring pristine baseline
- Service dependency topology graph
- Service name normalization across simulator methods
"""
from __future__ import annotations

import pytest
from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario, ServiceHealth, LogSeverity


@pytest.fixture(autouse=True)
def clean_cluster():
    """Ensure every test runs against a clean, baseline cloud state."""
    cloud.reset()
    yield
    cloud.reset()


# =============================================================================
# Baseline Operational Invariants
# =============================================================================

def test_baseline_cluster_has_four_services():
    telemetry = cloud.get_telemetry()
    assert len(telemetry) == 4
    names = [t.service_name for t in telemetry]
    assert "api-gateway" in names
    assert "order-service" in names
    assert "payment-gateway" in names
    assert "inventory-worker" in names


def test_baseline_all_services_healthy():
    for t in cloud.get_telemetry():
        assert t.status == ServiceHealth.HEALTHY
        assert t.error_rate_pct == 0.0


def test_baseline_latencies_within_sla():
    for t in cloud.get_telemetry():
        assert t.p50_latency_ms <= 25.0
        assert t.p95_latency_ms <= 50.0
        assert t.p99_latency_ms <= 60.0


def test_baseline_resource_consumption():
    for t in cloud.get_telemetry():
        assert t.memory_usage_mb <= 300.0
        assert t.cpu_usage_pct <= 25.0
        assert t.requests_per_sec > 100.0


def test_baseline_queue_is_healthy():
    q = cloud.get_queue_state()
    assert q.queue_name == "order-processing-queue"
    assert q.dead_letter_count == 0
    assert len(q.poison_pill_ids) == 0
    assert q.approximate_messages_visible == 12


def test_baseline_instance_counts():
    assert cloud.instance_counts["api-gateway"] == 2
    assert cloud.instance_counts["order-service"] == 3
    assert cloud.instance_counts["payment-gateway"] == 2
    assert cloud.instance_counts["inventory-worker"] == 2


def test_baseline_no_active_incident():
    assert cloud.active_incident is None
    assert cloud.active_chaos is None


def test_baseline_topology_dependencies():
    topo = cloud.get_topology()
    assert "order-service" in topo["api-gateway"]
    assert "payment-gateway" in topo["order-service"]
    assert "order-processing-queue" in topo["order-service"]
    assert "order-processing-queue" in topo["inventory-worker"]
    assert topo["payment-gateway"] == []


# =============================================================================
# Chaos Scenario Injections
# =============================================================================

def test_chaos_sqs_poison_pill_injection():
    inc = cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    assert inc.severity.value == "SEV1"
    assert inc.status == "OPEN"
    assert "inventory-worker" in inc.affected_services
    assert cloud.queue.dead_letter_count == 18
    assert len(cloud.queue.poison_pill_ids) == 3
    assert cloud.queue.approximate_messages_visible == 450


def test_chaos_sqs_telemetry_degradation():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    worker_telemetry = cloud.get_telemetry("inventory-worker")[0]
    assert worker_telemetry.status == ServiceHealth.CRITICAL
    assert worker_telemetry.error_rate_pct > 80.0
    assert worker_telemetry.p99_latency_ms > 400.0


def test_chaos_sqs_logs_contain_stack_trace():
    cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
    logs = cloud.get_logs("inventory-worker", limit=5)
    assert len(logs) > 0
    assert any("JSONDecodeError" in str(l.error_type) for l in logs)
    assert any("msg-bad-881" in str(l.message) for l in logs)


def test_chaos_memory_leak_oom_injection():
    inc = cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    assert inc.severity.value == "SEV1"
    assert "payment-gateway" in inc.affected_services
    telemetry = {t.service_name: t for t in cloud.get_telemetry()}
    assert telemetry["payment-gateway"].status == ServiceHealth.CRITICAL
    assert telemetry["payment-gateway"].p99_latency_ms > 3000.0
    assert telemetry["payment-gateway"].memory_usage_mb > 1900.0
    assert telemetry["order-service"].status == ServiceHealth.DEGRADED


def test_chaos_rate_limit_misconfig_injection():
    inc = cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    assert inc.severity.value == "SEV1"
    assert "api-gateway" in inc.affected_services
    assert cloud.service_configs["api-gateway"]["rate_limit_rps"] == 5
    telemetry = cloud.get_telemetry("api-gateway")[0]
    assert telemetry.status == ServiceHealth.CRITICAL
    assert telemetry.error_rate_pct > 85.0


def test_chaos_db_pool_starvation_injection():
    inc = cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)
    assert inc.severity.value == "SEV2"
    assert "order-service" in inc.affected_services
    telemetry = cloud.get_telemetry("order-service")[0]
    assert telemetry.status == ServiceHealth.CRITICAL
    assert telemetry.error_rate_pct > 60.0
    assert telemetry.p99_latency_ms > 1500.0


# =============================================================================
# Lifecycle, State Management & Logging
# =============================================================================

def test_cloud_reset_clears_chaos_and_restores_health():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    assert cloud.active_chaos is not None
    cloud.reset()
    assert cloud.active_chaos is None
    assert cloud.active_incident is None
    for t in cloud.get_telemetry():
        assert t.status == ServiceHealth.HEALTHY


def test_cloud_reset_restores_service_configs():
    cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
    assert cloud.service_configs["api-gateway"]["rate_limit_rps"] == 5
    cloud.reset()
    assert cloud.service_configs["api-gateway"]["rate_limit_rps"] == 500
    assert cloud.service_configs["api-gateway"]["version"] == "v1.8.2"


def test_cloud_reset_clears_draining_services():
    cloud.drain_service_traffic("payment-gateway")
    assert "payment-gateway" in cloud.draining_services
    cloud.reset()
    assert cloud.draining_services == []


def test_log_ring_buffer_structure():
    logs = cloud.get_logs(limit=10)
    assert len(logs) > 0
    for l in logs:
        assert l.timestamp is not None
        assert l.service is not None
        assert l.trace_id.startswith("trace-")
        assert isinstance(l.level, LogSeverity)


def test_log_filtering_by_service():
    cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
    payment_logs = cloud.get_logs("payment-gateway", limit=10)
    for l in payment_logs:
        assert l.service == "payment-gateway"


def test_telemetry_normalization_handles_various_formats():
    assert len(cloud.get_telemetry("payment-gateway")) == 1
    assert len(cloud.get_telemetry("Payment Gateway")) == 1
    assert len(cloud.get_telemetry("payment_gateway")) == 1
    assert len(cloud.get_telemetry("PAYMENT-GATEWAY")) == 1


def test_telemetry_query_for_all_returns_all_four():
    assert len(cloud.get_telemetry(None)) == 4
    assert len(cloud.get_telemetry("")) == 4
    assert len(cloud.get_telemetry("all")) == 4
