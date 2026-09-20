"""Remediation execution tool for StrandsOps.

Executes strictly bounded, typed self-healing actions on the cloud infrastructure
using the Pluggable SRE Runbook Registry.
Supported primitives:
- quarantine_messages   — isolate poison pills to DLQ (no data loss)
- restart_service       — graceful container reboot (flushes memory/pool leaks)
- rollback_config       — revert deployment to last known good version
- scale_service         — adjust instance count (capped at ±5 per operation)
- drain_traffic         — stop new requests, drain in-flight connections gracefully
- flush_cache           — flush stale Redis/ElastiCache keys causing data inconsistency
- trip_circuit_breaker  — shed load from degraded third-party downstream dependencies
- reroute_traffic       — shift traffic away from an impaired AWS Availability Zone
"""
from __future__ import annotations

import json
from strands import tool
from strandops.cloud_backend import cloud
from strandops.plugins.registry import registry

# Action alias mapping for natural SRE agent inputs
_ACTION_ALIASES = {
    "restart_container": "restart_service",
    "reboot_instance": "restart_service",
    "rollback_deployment": "rollback_config",
    "scale_instances": "scale_service",
    "scale_up": "scale_service",
    "scale_down": "scale_service",
    "drain_service": "drain_traffic",
    "drain_connections": "drain_traffic",
}


@tool
def execute_remediation(action_type: str, target: str, parameters_json: str = "{}") -> str:
    """Execute a self-healing remediation action on cloud infrastructure.

    Dispatches typed actions through the Pluggable SRE Runbook Registry.

    Args:
        action_type: The type of remediation:
                     - 'quarantine_messages' (moves poison pills to DLQ)
                     - 'restart_service' (gracefully reboots container to clear memory/hung pools)
                     - 'rollback_config' (reverts service deployment/config to stable tag)
                     - 'scale_service' (adds/removes instances, parameters: {"delta": N})
                     - 'drain_traffic' (drains active connections gracefully)
                     - 'flush_cache' (flushes stale cache keys, parameters: {"key_pattern": "*"})
                     - 'trip_circuit_breaker' (sheds traffic from failing API, parameters: {"shed_pct": 100})
                     - 'reroute_traffic' (shifts traffic between AZs, parameters: {"from_az": "us-east-1a", "to_az": "us-east-1b"})
        target: The target service, queue, or cache cluster (e.g. 'order-processing-queue', 'payment-gateway', 'redis-cluster').
        parameters_json: Optional JSON string of parameters (e.g. '{"delta": 2}' or '{"key_pattern": "order:*"}').
    """
    raw_action = action_type.strip().lower()
    canonical_action = _ACTION_ALIASES.get(raw_action, raw_action)
    tgt = target.strip().lower().replace(" ", "-").replace("_", "-")

    params = {}
    if parameters_json:
        try:
            params = json.loads(parameters_json)
        except json.JSONDecodeError:
            try:
                import ast
                params = ast.literal_eval(parameters_json)
            except Exception:
                params = {}

    result = registry.execute(cloud=cloud, action_name=canonical_action, target=tgt, parameters=params)

    if result.get("status") == "error" and "Unsupported action" in result.get("message", ""):
        return json.dumps({
            "status": "error",
            "message": f"Unsupported action '{action_type}'. Allowed: "
                       "['quarantine_messages', 'restart_service', 'rollback_config', 'scale_service', "
                       "'drain_traffic', 'flush_cache', 'trip_circuit_breaker', 'reroute_traffic']",
        })

    return json.dumps({
        "action_executed": canonical_action,
        "target": tgt,
        "result": result,
    }, indent=2)
