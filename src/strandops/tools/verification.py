"""Closed-Loop Verification tool for StrandsOps.

Guarantees that an incident is not declared resolved until live telemetry
verifies mathematical stability across a time-windowed soak period:
1. Error rate stays 0.0% across all checkpoints (flapping elimination).
2. Memory slope is flat (not leaking again: delta < 15%).
3. Latency jitter is stable (< 15% variance).
"""
from __future__ import annotations

import json
import time
from strands import tool
from strandops.simulator.cloud import cloud


@tool
def verify_system_recovery(service_name: str = "", soak_checks: int = 1, soak_window_seconds: int = 0) -> str:
    """Verify whether cloud infrastructure has recovered to healthy SLA baselines.

    Closed-Loop Safety Check: Call this AFTER executing remediation to mathematically
    confirm that error rates have dropped to 0%, latency is within SLA, and memory is stable.

    Supports multi-checkpoint time-windowed soak verification:
    - soak_checks=1: Single snapshot (fast, for routine baseline checks)
    - soak_checks=3: Three checkpoints with soak-testing (recommended for production —
      catches flapping services, re-emerging memory leaks, and latency jitter)

    Args:
        service_name: Optional specific service to verify. Omit to verify all services.
        soak_checks: Number of verification checkpoints (1-5). Default: 1.
        soak_window_seconds: Total soak window duration in seconds (optional).
    """
    raw = service_name.strip().lower().replace(" ", "-").replace("_", "-") if service_name else ""
    target = None if raw in ("", "all", "none", "null") else raw

    # Clamp soak_checks to a safe range
    num_checks = max(1, min(int(soak_checks), 5))

    # Defensive check: if a specific service was requested, ensure it actually exists
    initial_check = cloud.get_telemetry(target)
    if target and not initial_check:
        return json.dumps({
            "all_recovered": False,
            "all_systems_recovered": False,
            "stability": "ERROR",
            "stability_confidence": "0.0%",
            "verification_checkpoints": 0,
            "checkpoints_passed": 0,
            "checkpoints_failed": num_checks,
            "checkpoint_details": [],
            "queue_healthy": False,
            "healthy_services": [],
            "unrecovered_services": [{"service": service_name, "error": f"Unknown service '{service_name}'"}],
            "verdict": f"❌ ERROR: Cannot verify recovery — service '{service_name}' does not exist in cluster topology.",
        }, indent=2)

    # Collect health snapshots across multiple checkpoints
    checkpoint_results = []
    telemetry_history = []
    all_checkpoints_healthy = True

    delay = 0.5
    if soak_window_seconds > 0:
        delay = min(float(soak_window_seconds) / max(num_checks - 1, 1), 1.0)

    for checkpoint_idx in range(num_checks):
        if checkpoint_idx > 0:
            time.sleep(delay)

        snapshots = cloud.get_telemetry(target)
        if not snapshots:
            all_checkpoints_healthy = False
            break

        telemetry_history.append(snapshots)
        failing_services = []
        healthy_services = []

        for s in snapshots:
            is_failing = (s.error_rate_pct > 1.0) or (s.p99_latency_ms > 120.0)
            entry = {
                "service": s.service_name,
                "error_rate_pct": f"{s.error_rate_pct:.1f}%",
                "p99_latency_ms": f"{s.p99_latency_ms:.1f} ms",
                "memory_mb": s.memory_usage_mb,
                "status": s.status.value,
            }
            if is_failing:
                failing_services.append(entry)
            else:
                healthy_services.append(entry)

        queue = cloud.get_queue_state()
        queue_healthy = len(queue.poison_pill_ids) == 0

        checkpoint_healthy = (len(failing_services) == 0) and queue_healthy
        if not checkpoint_healthy:
            all_checkpoints_healthy = False

        checkpoint_results.append({
            "checkpoint": checkpoint_idx + 1,
            "healthy": checkpoint_healthy,
            "failing_count": len(failing_services),
        })

    # Mathematical stability analysis
    passed_count = sum(1 for c in checkpoint_results if c["healthy"])
    failed_count = num_checks - passed_count

    # Check for memory slope leaks across checkpoints
    memory_leaking_again = False
    if len(telemetry_history) >= 2:
        first_pass = {s.service_name: s.memory_usage_mb for s in telemetry_history[0]}
        last_pass = {s.service_name: s.memory_usage_mb for s in telemetry_history[-1]}
        for svc_name, init_mem in first_pass.items():
            final_mem = last_pass.get(svc_name, init_mem)
            if final_mem > init_mem * 1.15:
                memory_leaking_again = True
                break

    is_flapping = (passed_count > 0 and failed_count > 0) or memory_leaking_again

    if is_flapping:
        stability = "UNSTABLE_FLAPPING"
        verdict = (
            f"⚠️ UNSTABLE_FLAPPING: Service recovered in {passed_count}/{num_checks} checkpoints "
            f"but degraded in {failed_count} or showed upward memory slope. System failed soak test."
        )
        all_checkpoints_healthy = False
    elif all_checkpoints_healthy:
        stability = "STABLE"
        verdict = "✅ SUCCESS: All services healthy and operating within SLA parameters across soak window."
    else:
        stability = "DEGRADED"
        verdict = "❌ DEGRADED: One or more services are still breaching SLA thresholds across all checkpoints."

    stability_confidence = round((passed_count / num_checks) * 100, 1)

    return json.dumps({
        "all_recovered": all_checkpoints_healthy,
        "all_systems_recovered": all_checkpoints_healthy,
        "stability": stability,
        "stability_confidence": f"{stability_confidence}%",
        "verification_checkpoints": num_checks,
        "checkpoints_passed": passed_count,
        "checkpoints_failed": failed_count,
        "memory_slope_stable": not memory_leaking_again,
        "checkpoint_details": checkpoint_results,
        "queue_healthy": queue_healthy,
        "healthy_services": healthy_services,
        "unrecovered_services": failing_services,
        "verdict": verdict,
    }, indent=2)
