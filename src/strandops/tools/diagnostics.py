"""Diagnostics and root-cause analysis tools for StrandsOps.

Enables the SRE agent to fetch structured error logs and inspect SQS queues
to isolate specific poison pills, memory leak signatures, and stack traces.
"""
from __future__ import annotations

import json
from strands import tool
from strandops.cloud_backend import cloud
from strandops.simulator.models import LogSeverity

_ERROR_LEVELS = {LogSeverity.WARN, LogSeverity.ERROR, LogSeverity.FATAL}


@tool
def fetch_error_logs(service_name: str = "", limit: int = 10) -> str:
    """Fetch recent structured logs and stack traces from cloud services.

    Filters logs for WARN, ERROR, and FATAL severities to diagnose root causes
    of failing transactions or crashed workers.

    Args:
        service_name: Optional service to filter logs (e.g. 'inventory-worker',
                      'payment-gateway', 'order-service', 'api-gateway').
        limit: Maximum number of recent log entries to retrieve (1 to 50).
    """
    raw = service_name.strip().lower().replace(" ", "-").replace("_", "-") if service_name else ""
    target = None if raw in ("", "all", "none", "null") else raw
    limit = max(1, min(limit, 50))
    # Over-fetch then filter so WARN/ERROR/FATAL still fill the requested limit
    candidates = cloud.get_logs(service_name=target, limit=max(limit * 10, 50))
    logs = [l for l in candidates if l.level in _ERROR_LEVELS][-limit:]

    log_entries = []
    for l in logs:
        log_entries.append({
            "timestamp": l.timestamp,
            "service": l.service,
            "level": l.level.value,
            "trace_id": l.trace_id,
            "message": l.message,
            "error_type": l.error_type,
            "stack_trace": l.stack_trace,
            "metadata": l.metadata,
        })

    return json.dumps({
        "total_logs": len(log_entries),
        "filter_service": service_name or "ALL",
        "severity_filter": ["WARN", "ERROR", "FATAL"],
        "entries": log_entries,
    }, indent=2)


@tool
def inspect_queue_health(queue_name: str = "order-processing-queue") -> str:
    """Inspect the status, depth, and poison-pill messages of an AWS SQS queue.

    Returns the visible message backlog, dead-letter queue count, and the exact
    message IDs identified as unparseable poison pills.

    Args:
        queue_name: The name of the SQS queue to inspect (default: 'order-processing-queue').
    """
    q = cloud.get_queue_state()
    normalized = queue_name.strip().lower().replace(" ", "-").replace("_", "-")
    if q.queue_name.lower().replace(" ", "-").replace("_", "-") != normalized:
        return json.dumps({
            "status": "error",
            "message": f"Queue '{queue_name}' not found. Available: ['{q.queue_name}']"
        })

    return json.dumps({
        "queue_name": q.queue_name,
        "approximate_messages_visible": q.approximate_messages_visible,
        "dead_letter_queue": q.dead_letter_queue_name,
        "dead_letter_count": q.dead_letter_count,
        "poison_pill_ids": q.poison_pill_ids,
        "has_poison_pills": len(q.poison_pill_ids) > 0,
        "health": "CRITICAL" if q.poison_pill_ids else "HEALTHY",
    }, indent=2)
