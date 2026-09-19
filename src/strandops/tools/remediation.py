"""Remediation execution tool for StrandsOps.

Executes strictly bounded, typed self-healing actions on the cloud infrastructure
(quarantine poison pills, restart hung services, rollback bad configs).
"""
from __future__ import annotations

import json
from strands import tool
from strandops.simulator.cloud import cloud


@tool
def execute_remediation(action_type: str, target: str, parameters_json: str = "{}") -> str:
    """Execute a self-healing remediation action on cloud infrastructure.

    Only accepts bounded, typed remediation primitives to guarantee safety.

    Args:
        action_type: The type of remediation:
                     - 'quarantine_messages' (moves poison pills to dead-letter queue)
                     - 'restart_service' (gracefully reboots a container to clear memory leaks / hung pools)
                     - 'rollback_config' (reverts service deployment/config to previous stable tag)
        target: The target service or queue (e.g. 'order-processing-queue', 'payment-gateway', 'api-gateway').
        parameters_json: Optional JSON string of parameters (e.g. '{"message_ids": ["msg-bad-881", "msg-bad-882"]}').
    """
    action = action_type.strip().lower()
    tgt = target.strip()

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

    if action == "quarantine_messages":
        message_ids = params.get("message_ids", [])
        if not message_ids:
            # Check if queue has known poison pill IDs
            q = cloud.get_queue_state()
            message_ids = q.poison_pill_ids

        result = cloud.quarantine_queue_messages(queue_name=tgt, message_ids=message_ids)
        return json.dumps({
            "action_executed": "quarantine_messages",
            "target": tgt,
            "result": result,
        }, indent=2)

    elif action in ("restart_service", "restart_container", "reboot_instance"):
        result = cloud.restart_service_instance(service_name=tgt)
        return json.dumps({
            "action_executed": "restart_service",
            "target": tgt,
            "result": result,
        }, indent=2)

    elif action in ("rollback_config", "rollback_deployment"):
        result = cloud.rollback_service_config(service_name=tgt)
        return json.dumps({
            "action_executed": "rollback_config",
            "target": tgt,
            "result": result,
        }, indent=2)

    else:
        return json.dumps({
            "status": "error",
            "message": f"Unsupported action '{action_type}'. Allowed: ['quarantine_messages', 'restart_service', 'rollback_config']",
        })
