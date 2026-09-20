"""Blast Radius & Safety Gate tool for StrandsOps.

Evaluates the architectural impact of a proposed remediation action before execution
to prevent cascading failures across the microservice topology.
"""
from __future__ import annotations

import json
import os
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

    # Safety threshold from config — how many downstream dependents we allow
    # before requiring human approval
    blast_limit = int(os.getenv("AUTO_REMEDIATE_BLAST_LIMIT", "2"))

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
            rationale.append(f"Blast radius: {len(dependents)} direct dependent(s) ({', '.join(dependents) or 'none'}).")
            # Only auto-approve if dependents are within the configurable safety limit
            safe_to_proceed = len(dependents) <= blast_limit
            if not safe_to_proceed:
                rationale.append(f"⚠️ BLOCKED: {len(dependents)} dependents exceed auto-remediate limit ({blast_limit}). Requires human approval.")
            else:
                rationale.append(f"Auto-approved: {len(dependents)} dependent(s) within safety threshold ({blast_limit}).")
        else:
            risk_level = "LOW"
            rationale.append(f"Standard container reboot on {target}.")

    elif "rollback" in action:
        risk_level = "LOW"
        rationale.append(f"Rolling back configuration on {target} reverts bad rate limit parameters to tested stable baseline.")

    elif "drain" in action:
        risk_level = "MEDIUM"
        rationale.append(f"Draining traffic from {target} will redirect requests to other instances.")
        rationale.append(f"Upstream callers ({', '.join(dependents) or 'none'}) may see brief latency increase during failover.")

    elif "scale" in action:
        risk_level = "LOW"
        rationale.append(f"Scaling {target} adjusts instance count without interrupting active traffic.")
        rationale.append("Instance count is clamped to [1, 10] with a maximum delta of ±5 per operation.")

    else:
        # Unknown action — default to HIGH risk and block
        risk_level = "HIGH"
        safe_to_proceed = False
        rationale.append(f"Unknown action '{proposed_action}'. Cannot assess blast radius for unrecognized operations.")
        rationale.append("Manual review required before execution.")

    assessment = {
        "target": target,
        "proposed_action": proposed_action,
        "direct_dependents": dependents,
        "dependent_count": len(dependents),
        "blast_limit_threshold": blast_limit,
        "risk_level": risk_level,
        "safe_to_proceed": safe_to_proceed,
        "safety_rationale": rationale,
        "recommended_precaution": (
            "⚠️ Requires human approval — blast radius exceeds safety threshold."
            if not safe_to_proceed
            else "Ensure traffic retries are enabled on upstream callers."
            if risk_level in ("MEDIUM", "HIGH")
            else "Proceed with standard execution."
        ),
    }

    return json.dumps(assessment, indent=2)
