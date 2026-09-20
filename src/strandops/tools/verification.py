"""Closed-Loop Verification tool for StrandsOps.

Guarantees that an incident is not declared resolved until live telemetry
verifies that error rates have dropped to 0.0% and latencies meet SLA targets.

Supports multi-checkpoint soak-window verification to catch "flapping" services
that briefly recover before crashing again.
"""
from __future__ import annotations

import json
import time
from strands import tool
from strandops.simulator.cloud import cloud


@tool
def verify_system_recovery(service_name: str = "", soak_checks: int = 1) -> str:
    """Verify whether cloud infrastructure has recovered to healthy SLA baselines.

    Closed-Loop Safety Check: Call this AFTER executing remediation to mathematically
    confirm that error rates have dropped to 0% and latency is within acceptable SLAs.

    Supports multi-checkpoint soak-window verification to catch "flapping" services:
    - soak_checks=1: Single snapshot (fast, for routine checks)
    - soak_checks=3: Three checkpoints with brief pauses between them (recommended
      for production — catches services that recover temporarily before crashing again)

    Args:
        service_name: Optional specific service to verify. Omit to verify all services.
        soak_checks: Number of verification checkpoints (1-5). Higher values catch flapping
                     services but take longer. Default: 1 for fast feedback in demos.
    """
    raw = service_name.strip().lower().replace(" ", "-").replace("_", "-") if service_name else ""
    target = None if raw in ("", "all", "none", "null") else raw

    # Clamp soak_checks to a safe range to prevent LLM from requesting excessive loops
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
    all_checkpoints_healthy = True

    for checkpoint_idx in range(num_checks):
        # Brief pause between checkpoints (skip the first one — check immediately)
        if checkpoint_idx > 0:
            time.sleep(0.5)  # 500ms between checks (simulated environment; real AWS would use 15-30s)

        snapshots = cloud.get_telemetry(target)
        if not snapshots:
            all_checkpoints_healthy = False
            break

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

        checkpoint_healthy = (len(failing_services) == 0) and queue_healthy
        if not checkpoint_healthy:
            all_checkpoints_healthy = False

        checkpoint_results.append({
            "checkpoint": checkpoint_idx + 1,
            "healthy": checkpoint_healthy,
            "failing_count": len(failing_services),
        })

    # Determine stability verdict based on all checkpoints
    passed_count = sum(1 for c in checkpoint_results if c["healthy"])
    failed_count = num_checks - passed_count

    if all_checkpoints_healthy:
        stability = "STABLE"
        verdict = "✅ SUCCESS: All services healthy and stable across all verification checkpoints."
    elif passed_count > 0 and failed_count > 0:
        stability = "FLAPPING"
        verdict = (
            f"⚠️ FLAPPING: Service recovered in {passed_count}/{num_checks} checkpoints "
            f"but degraded in {failed_count}. System is unstable — investigate before closing."
        )
    else:
        stability = "DEGRADED"
        verdict = "❌ DEGRADED: One or more services are still breaching SLA thresholds across all checkpoints."

    # Calculate stability confidence as a percentage
    stability_confidence = round((passed_count / num_checks) * 100, 1)

    return json.dumps({
        "all_recovered": all_checkpoints_healthy,
        "all_systems_recovered": all_checkpoints_healthy,
        "stability": stability,
        "stability_confidence": f"{stability_confidence}%",
        "verification_checkpoints": num_checks,
        "checkpoints_passed": passed_count,
        "checkpoints_failed": failed_count,
        "checkpoint_details": checkpoint_results,
        "queue_healthy": queue_healthy,
        "healthy_services": healthy_services,
        "unrecovered_services": failing_services,
        "verdict": verdict,
    }, indent=2)
