"""Telemetry inspection tool for StrandsOps.

Allows the SRE agent to observe real-time metrics across microservices,
comparing against SLA benchmarks.
"""
from __future__ import annotations

import json
from strands import tool
from strandops.cloud_backend import cloud, list_known_services
from strandops.sla import is_sla_breached, max_error_rate_pct, max_p99_latency_ms


@tool
def inspect_telemetry(service_name: str = "") -> str:
    """Inspect real-time telemetry metrics for microservices and cloud infrastructure.

    Returns latency (P50, P95, P99), error rates, throughput (RPS), and memory
    consumption. Highlights any metrics exceeding SLA thresholds.

    Args:
        service_name: Optional name of the service to inspect (e.g. 'inventory-worker',
                      'payment-gateway', 'order-service', 'api-gateway').
                      Omit to inspect all services across the topology.
    """
    raw = service_name.strip().lower().replace(" ", "-").replace("_", "-") if service_name else ""
    target = None if raw in ("", "all", "none", "null") else raw
    snapshots = cloud.get_telemetry(target)

    if not snapshots:
        return json.dumps({
            "status": "error",
            "message": f"Service '{service_name}' not found. Available: {list_known_services()}"
        })

    report = []
    for s in snapshots:
        sla_violation = is_sla_breached(s.error_rate_pct, s.p99_latency_ms)
        report.append({
            "service": s.service_name,
            "status": s.status.value,
            "sla_breached": sla_violation,
            "p50_latency_ms": s.p50_latency_ms,
            "p95_latency_ms": s.p95_latency_ms,
            "p99_latency_ms": s.p99_latency_ms,
            "error_rate_pct": f"{s.error_rate_pct:.1f}%",
            "requests_per_sec": s.requests_per_sec,
            "memory_usage_mb": f"{s.memory_usage_mb:.1f} MB",
            "cpu_usage_pct": f"{s.cpu_usage_pct:.1f}%",
        })

    return json.dumps({
        "timestamp": snapshots[0].timestamp.isoformat(),
        "services_inspected": len(report),
        "sla_thresholds": {
            "max_error_rate_pct": max_error_rate_pct(),
            "max_p99_latency_ms": max_p99_latency_ms(),
        },
        "telemetry": report,
    }, indent=2)
