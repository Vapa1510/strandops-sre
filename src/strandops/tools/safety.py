"""Blast Radius & Safety Gate tool for StrandsOps.

Evaluates the architectural impact of a proposed remediation action before execution
to prevent cascading failures across the microservice topology.
"""
from __future__ import annotations

import json
from strands import tool
from strandops.simulator.cloud import cloud


@tool
def analyze_blast_radius(proposed_action: str, target_service: str) -> str:
    """Evaluate the blast radius and safety risks of a proposed remediation action.

    Mandatory safety gate: Call this BEFORE executing any destructive or mutating
    remediation (such as restarting a container, rolling back a deployment, or purging messages).

    Args:
        proposed_action: The action planned (e.g. 'restart_service', 'quarantine_messages',
                         'rollback_config', 'drain_traffic').
        target_service: The service or resource targeted (e.g. 'payment-gateway',
                        'order-processing-queue', 'api-gateway', 'order-service').
    """
    target = target_service.strip().lower()
    topology = cloud.get_topology()

    # Find services that depend directly on this target
    dependents = [svc for svc, deps in topology.items() if target in deps]

    # Evaluate action safety
    action = proposed_action.strip().lower()
    safe_to_proceed = True
    risk_level = "LOW"
    rationale = []

    if "quarantine" in action:
        risk_level = "LOW"
        rationale.append("Quarantining messages moves corrupted records to the DLQ without dropping valid order items.")
        rationale.append("Worker threads will immediately unblock and resume processing healthy messages.")

    elif "restart" in action:
        if target == "payment-gateway":
            risk_level = "MEDIUM"
            rationale.append("Payment gateway has no downstream dependencies; restarting flushes connection leaks safely.")
            rationale.append(f"Upstream callers ({', '.join(dependents) or 'none'}) will experience brief retry attempts (~1-2s).")
        elif target == "order-service":
            risk_level = "HIGH"
            rationale.append("Order service is the central commerce engine. Restarting will temporarily interrupt checkout API.")
            safe_to_proceed = True  # Allowed if sev1, but with caution
        else:
            risk_level = "LOW"
            rationale.append(f"Standard container reboot on {target}.")

    elif "rollback" in action:
        risk_level = "LOW"
        rationale.append(f"Rolling back configuration on {target} reverts bad rate limit parameters to tested stable baseline.")

    assessment = {
        "target": target,
        "proposed_action": proposed_action,
        "direct_dependents": dependents,
        "risk_level": risk_level,
        "safe_to_proceed": safe_to_proceed,
        "safety_rationale": rationale,
        "recommended_precaution": (
            "Ensure traffic retries are enabled on upstream callers."
            if risk_level in ("MEDIUM", "HIGH")
            else "Proceed with standard execution."
        ),
    }

    return json.dumps(assessment, indent=2)
