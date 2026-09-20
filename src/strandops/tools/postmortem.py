"""Postmortem generator for StrandsOps.

Builds a Markdown incident write-up: timeline, root cause, MTTR, fixes, and follow-ups.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from strands import tool
from strandops.cloud_backend import cloud
from strandops.simulator.models import ChaosScenario
from strandops.sla import is_sla_breached, max_error_rate_pct, max_p99_latency_ms


_RCA_MAP = {
    ChaosScenario.SQS_POISON_PILL: {
        "rca": (
            "* Corrupted message payloads entered the `order-processing-queue` without upfront schema validation.\n"
            "* Worker threads in `inventory-worker` hit `json.decoder.JSONDecodeError` on 3 malformed messages "
            "(msg-bad-881, msg-bad-882, msg-bad-883), triggering exponential retries.\n"
            "* Valid customer orders backed up behind the poison pills, causing a 450-message backlog."
        ),
        "actions": [
            ("Implement strict JSON schema validation at the SQS ingestion gateway", "Preventative", "App Team", "Planned"),
            ("Add Dead-Letter Queue alert threshold at > 5 items", "Monitoring", "SRE Team", "In Progress"),
            ("Keep quarantine playbook for poison pills in the on-call runbook", "Process", "On-Call", "Completed"),
        ],
    },
    ChaosScenario.MEMORY_LEAK_OOM: {
        "rca": (
            "* Unclosed HTTP connection pool in the `payment-gateway` Stripe client accumulated 980/1000 open connections.\n"
            "* Memory climbed to 1,940 MB (near 2,048 MB container limit), triggering GC thrashing and 504 Gateway Timeouts.\n"
            "* P99 latency degraded to 3,450 ms as the connection pool exhausted available file descriptors."
        ),
        "actions": [
            ("Implement connection pool max-age limits (idle timeout: 60s, max lifetime: 300s)", "Preventative", "App Team", "Planned"),
            ("Add memory usage alerting threshold at 80% of container limit", "Monitoring", "SRE Team", "In Progress"),
            ("Enforce `contextmanager` / `async with` patterns for all HTTP client sessions", "Code Quality", "App Team", "Planned"),
        ],
    },
    ChaosScenario.RATE_LIMIT_MISCONFIG: {
        "rca": (
            "* A Friday deployment (v1.8.3) misconfigured the API Gateway rate limiter from 500 RPS to 5 RPS.\n"
            "* 89.2% of legitimate customer traffic was rejected with HTTP 429 (Too Many Requests).\n"
            "* The misconfiguration was not caught by CI/CD validation or canary analysis."
        ),
        "actions": [
            ("Add config validation gate in CI/CD pipeline to catch rate-limit values below minimum threshold", "Preventative", "Platform Team", "Planned"),
            ("Implement canary deployment with traffic-shadow comparison before full rollout", "Process", "SRE Team", "Planned"),
            ("Add config-drift checks to the standard rollback playbook", "Process", "On-Call", "Completed"),
        ],
    },
    ChaosScenario.DB_CONNECTION_STARVATION: {
        "rca": (
            "* Database connection pool in `order-service` reached maximum capacity (50/50 active, 120 requests waiting).\n"
            "* Long-running transactions held connections open, starving new checkout requests.\n"
            "* SQLAlchemy `QueuePool` timeout errors cascaded, causing P99 latency to spike to 1,800 ms."
        ),
        "actions": [
            ("Configure statement-level timeouts (30s max) to prevent long-running transaction lock-ups", "Preventative", "App Team", "Planned"),
            ("Increase connection pool overflow capacity from 10 to 25 with idle reclamation", "Capacity", "DBA Team", "Planned"),
            ("Add connection pool utilization metric to CloudWatch dashboard with 80% threshold alert", "Monitoring", "SRE Team", "In Progress"),
        ],
    },
}

_DEFAULT_RCA = {
    "rca": (
        "* Telemetry and structured error logs pointed to an acute failure across the affected services.\n"
        "* On-call triage correlated logs and metrics to isolate the failing component."
    ),
    "actions": [
        ("Review and address the identified root cause with the application team", "Preventative", "App Team", "Planned"),
        ("Add monitoring coverage for the failure mode detected", "Monitoring", "SRE Team", "Planned"),
        ("Update the on-call runbook with the remediation that worked", "Process", "On-Call", "Completed"),
    ],
}


@tool
def generate_incident_postmortem(incident_title: str = "") -> str:
    """Generate a Markdown incident postmortem for engineering leadership.

    Call this AFTER recovery has been verified. Summarizes timeline, root cause,
    MTTR, remediation steps, and follow-up work.

    Args:
        incident_title: Optional custom title for the postmortem report.
    """
    incident = cloud.active_incident
    chaos = cloud.active_chaos
    now = datetime.now(timezone.utc)

    title = incident_title.strip() or (incident.title if incident else "Cloud Incident Remediation")
    incident_id = incident.incident_id if incident else "INC-MANUAL-01"
    severity = incident.severity.value if incident else "SEV1"
    detected_at = incident.detected_at if incident else now
    resolved_at = incident.resolved_at if (incident and incident.resolved_at) else now
    affected = incident.affected_services if incident else ["cloud-infrastructure"]
    actions = incident.remediation_actions_taken if incident else ["Manual triage and remediation by on-call"]

    mttr_seconds = (resolved_at - detected_at).total_seconds()
    if mttr_seconds < 1:
        mttr_display = "< 1 second"
    elif mttr_seconds < 60:
        mttr_display = f"~{mttr_seconds:.0f} seconds"
    else:
        mttr_display = f"~{mttr_seconds / 60:.1f} minutes"

    mttd_display = "Alert on SLA breach (ops monitor)"

    scenario_key = chaos
    if scenario_key is None and incident:
        title_lower = incident.title.lower()
        if "poison" in title_lower or "sqs" in title_lower:
            scenario_key = ChaosScenario.SQS_POISON_PILL
        elif "memory" in title_lower or "oom" in title_lower or "leak" in title_lower:
            scenario_key = ChaosScenario.MEMORY_LEAK_OOM
        elif "rate" in title_lower or "misconfig" in title_lower or "429" in title_lower:
            scenario_key = ChaosScenario.RATE_LIMIT_MISCONFIG
        elif "connection" in title_lower or "starvation" in title_lower or "pool" in title_lower or "db" in title_lower:
            scenario_key = ChaosScenario.DB_CONNECTION_STARVATION

    rca_data = _RCA_MAP.get(scenario_key, _DEFAULT_RCA)

    postmortem_md = f"""# Incident Postmortem: {title}
**Incident ID:** `{incident_id}` | **Severity:** `{severity}` | **Status:** `RESOLVED`

---

## 1. Executive Summary
On {detected_at.isoformat()[:10]}, an alert fired for critical degradation in **{', '.join(affected)}**.
On-call triage reviewed telemetry and logs, checked blast radius before acting, applied a targeted fix, and re-checked metrics before closing the incident.

* **Mean Time to Detect (MTTD):** {mttd_display}
* **Mean Time to Resolve (MTTR):** {mttr_display} (detection to verified recovery)
* **Customer Impact:** Contained before wider upstream failure.

---

## 2. Root Cause Analysis (RCA)
{rca_data['rca']}

---

## 3. Remediation Actions Executed
"""
    for idx, act in enumerate(actions, 1):
        postmortem_md += f"{idx}. {act}\n"

    live_telemetry = cloud.get_telemetry()
    live_queue = cloud.get_queue_state()
    max_live_err = max((t.error_rate_pct for t in live_telemetry), default=0.0)
    max_live_p99 = max((t.p99_latency_ms for t in live_telemetry), default=0.0)
    queue_backlog = live_queue.approximate_messages_visible
    dlq_count = live_queue.dead_letter_count
    sla_err = max_error_rate_pct()
    sla_p99 = max_p99_latency_ms()
    all_within_sla = (
        not any(is_sla_breached(t.error_rate_pct, t.p99_latency_ms) for t in live_telemetry)
        and len(live_queue.poison_pill_ids) == 0
    )
    proof_status = "VERIFIED HEALTHY" if all_within_sla else "DEGRADED (ACTION REQUIRED)"

    postmortem_md += f"""
---

## 4. Closed-Loop Verification Proof ({proof_status})
* **Peak Error Rate:** {max_live_err:.1f}% (SLA: <= {sla_err}%)
* **P99 Latency:** {max_live_p99:.1f} ms (SLA: <= {sla_p99} ms)
* **Queue Backlog:** {queue_backlog} visible messages | DLQ: {dlq_count} quarantined
* **System Health:** {"Metrics within SLA across the cluster" if all_within_sla else "Warning: metrics still outside SLA — keep investigating"}

---

## 5. Preventative Action Items
| Action Item | Type | Owner | Status |
|---|---|---|---|
"""
    for item, item_type, owner, status in rca_data["actions"]:
        postmortem_md += f"| {item} | {item_type} | {owner} | {status} |\n"

    postmortem_md += f"""
*Report written by StrandsOps at {now.isoformat()}.*
"""

    return json.dumps({
        "status": "success",
        "incident_id": incident_id,
        "markdown_report": postmortem_md,
    }, indent=2)
