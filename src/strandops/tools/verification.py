"""Closed-Loop Verification tool for StrandsOps.

Guarantees that an incident is not declared resolved until live telemetry
verifies that error rates have dropped to 0.0% and latencies meet SLA targets.
"""
from __future__ import annotations

import json
from strands import tool
from strandops.simulator.cloud import cloud


@tool
def verify_system_recovery(service_name: str = "") -> str:
    """Verify whether cloud infrastructure has recovered to healthy SLA baselines.

    Closed-Loop Safety Check: Call this AFTER executing remediation to mathematically
    confirm that error rates have dropped to 0% and latency is within acceptable SLAs.

    Args:
        service_name: Optional specific service to verify. Omit to verify all services.
    """
    target = service_name.strip() if service_name else None
    snapshots = cloud.get_telemetry(target)

    failing_services = []
    healthy_services = []

    for s in snapshots:
        is_failing = (s.error_rate_pct > 1.0) or (s.p99_latency_ms > 120.0)
        entry = {
            "service": s.service_name,
            "error_rate_pct": f"{s.error_rate_pct:.1f}%",
            "p99_latency_ms": f"{s.p99_latency_ms:.1f} ms",
            "status": s.status.value,
        }
        if is_failing:
            failing_services.append(entry)
        else:
            healthy_services.append(entry)

    queue = cloud.get_queue_state()
    queue_healthy = len(queue.poison_pill_ids) == 0

    all_recovered = (len(failing_services) == 0) and queue_healthy

    return json.dumps({
        "all_recovered": all_recovered,
        "all_systems_recovered": all_recovered,
        "queue_healthy": queue_healthy,
        "healthy_services": healthy_services,
        "unrecovered_services": failing_services,
        "verdict": (
            "✅ SUCCESS: All services healthy and operating within SLA parameters."
            if all_recovered
            else "❌ DEGRADED: One or more services are still breaching SLA thresholds."
        ),
    }, indent=2)
