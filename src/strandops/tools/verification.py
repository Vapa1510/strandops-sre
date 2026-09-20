"""Recovery verification for StrandsOps.

An incident is not closed until live telemetry stays stable across a soak window.
Thresholds (must match the checks below; overridable via env):
1. Per-checkpoint SLA: error rate ≤ SLA_MAX_ERROR_RATE_PERCENT (default 1.0%)
   and P99 latency ≤ SLA_MAX_P99_LATENCY_MS (default 120 ms).
2. Memory slope: final memory must stay within +15% of the first checkpoint.
3. Latency jitter: P99 must not rise more than +20% across the soak window.
4. Queue: no poison-pill messages remaining.
"""
from __future__ import annotations

import json
import time
from strands import tool
from strandops.simulator.cloud import cloud
from strandops.sla import is_sla_breached, max_error_rate_pct, max_p99_latency_ms


@tool
def verify_system_recovery(service_name: str = "", soak_checks: int = 1, soak_window_seconds: int = 0) -> str:
    """Verify whether cloud infrastructure has recovered to healthy SLA baselines.

    Call this AFTER remediation. Confirms error rate and P99 stay within SLA,
    memory is stable, and the queue has no remaining poison pills.

    Supports multi-checkpoint soak verification:
    - soak_checks=1: Single snapshot (fast baseline check)
    - soak_checks=3: Three checkpoints (recommended — catches flapping and memory creep)

    Args:
        service_name: Optional specific service to verify. Omit to verify all services.
        soak_checks: Number of verification checkpoints (1-5). Default: 1.
        soak_window_seconds: Total soak window duration in seconds (optional).
    """
    raw = service_name.strip().lower().replace(" ", "-").replace("_", "-") if service_name else ""
    target = None if raw in ("", "all", "none", "null") else raw

    num_checks = max(1, min(int(soak_checks), 5))
    sla_err = max_error_rate_pct()
    sla_p99 = max_p99_latency_ms()

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
            "verdict": (
                f"Cannot verify recovery - service '{service_name}' "
                "does not exist in the cluster topology."
            ),
        }, indent=2)

    checkpoint_results = []
    telemetry_history = []
    all_checkpoints_healthy = True

    all_failing_services = []
    failing_services = []
    healthy_services = []
    queue = cloud.get_queue_state()
    queue_healthy = len(queue.poison_pill_ids) == 0

    delay = 0.5
    if soak_window_seconds > 0:
        delay = min(float(soak_window_seconds) / max(num_checks - 1, 1), 1.0)

    for checkpoint_idx in range(num_checks):
        if checkpoint_idx > 0:
            time.sleep(delay)

        snapshots = cloud.get_telemetry(target)
        if not snapshots:
            all_checkpoints_healthy = False
            checkpoint_results.append({
                "checkpoint": checkpoint_idx + 1,
                "healthy": False,
                "failing_count": -1,
                "error": "no telemetry returned",
            })
            continue

        telemetry_history.append(snapshots)
        failing_services = []
        healthy_services = []

        for s in snapshots:
            is_failing = is_sla_breached(s.error_rate_pct, s.p99_latency_ms)
            entry = {
                "service": s.service_name,
                "error_rate_pct": f"{s.error_rate_pct:.1f}%",
                "p99_latency_ms": f"{s.p99_latency_ms:.1f} ms",
                "memory_mb": s.memory_usage_mb,
                "status": s.status.value,
            }
            if is_failing:
                failing_services.append(entry)
                if not any(f["service"] == entry["service"] for f in all_failing_services):
                    all_failing_services.append(entry)
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

    passed_count = sum(1 for c in checkpoint_results if c["healthy"])
    failed_count = num_checks - passed_count

    memory_leaking_again = False
    if len(telemetry_history) >= 2:
        first_pass = {s.service_name: s.memory_usage_mb for s in telemetry_history[0]}
        last_pass = {s.service_name: s.memory_usage_mb for s in telemetry_history[-1]}
        for svc_name, init_mem in first_pass.items():
            final_mem = last_pass.get(svc_name, init_mem)
            if final_mem > init_mem * 1.15:
                memory_leaking_again = True
                break

    latency_jitter_unstable = False
    if len(telemetry_history) >= 2:
        first_lat = {s.service_name: s.p99_latency_ms for s in telemetry_history[0]}
        last_lat = {s.service_name: s.p99_latency_ms for s in telemetry_history[-1]}
        for svc_name, init_p99 in first_lat.items():
            final_p99 = last_lat.get(svc_name, init_p99)
            if init_p99 > 0 and (final_p99 - init_p99) / init_p99 > 0.20:
                latency_jitter_unstable = True
                break

    is_flapping = (passed_count > 0 and failed_count > 0) or memory_leaking_again or latency_jitter_unstable

    if is_flapping:
        stability = "UNSTABLE_FLAPPING"
        verdict = (
            f"UNSTABLE: Passed {passed_count}/{num_checks} checkpoints but failed "
            f"{failed_count} or showed rising memory / latency jitter. Soak check failed."
        )
        all_checkpoints_healthy = False
        stability_confidence = round(min((passed_count / num_checks) * 100, 50.0), 1)
    elif all_checkpoints_healthy:
        stability = "STABLE"
        verdict = (
            f"SUCCESS: Services within SLA (err ≤ {sla_err}%, P99 ≤ {sla_p99} ms) "
            "across the soak window."
        )
        stability_confidence = round((passed_count / num_checks) * 100, 1)
    else:
        stability = "DEGRADED"
        verdict = (
            f"DEGRADED: One or more services still breach SLA "
            f"(err ≤ {sla_err}% / P99 ≤ {sla_p99} ms) across checkpoints."
        )
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
        "latency_jitter_stable": not latency_jitter_unstable,
        "checkpoint_details": checkpoint_results,
        "queue_healthy": queue_healthy,
        "healthy_services": healthy_services,
        "unrecovered_services": all_failing_services if is_flapping else failing_services,
        "verdict": verdict,
    }, indent=2)
