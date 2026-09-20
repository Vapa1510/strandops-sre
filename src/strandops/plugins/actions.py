"""Typed SRE Remediation Action Plugins.

Defines standard self-healing runbook primitives as typed Pydantic models.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from strandops.plugins.base import RemediationPlugin


class QuarantineMessagesPlugin(RemediationPlugin):
    """Isolate corrupted poison pill messages to the Dead-Letter Queue."""
    action_name: str = "quarantine_messages"
    description: str = "Moves corrupted messages to DLQ to prevent consumer retry crashes"
    risk_level: str = "LOW"
    allowed_services: List[str] = ["order-processing-queue", "*"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        message_ids = parameters.get("message_ids", [])
        if not message_ids:
            q = cloud.get_queue_state()
            message_ids = q.poison_pill_ids
        return cloud.quarantine_queue_messages(queue_name=target, message_ids=message_ids)


class RestartServicePlugin(RemediationPlugin):
    """Gracefully reboots a microservice container to clear memory leaks & hung pools."""
    action_name: str = "restart_service"
    description: str = "Gracefully reboots container instance, resetting connection pools and memory"
    risk_level: str = "MEDIUM"
    allowed_services: List[str] = ["payment-gateway", "order-service", "api-gateway", "inventory-worker"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return cloud.restart_service_instance(service_name=target)

    def evaluate_blast_radius(self, cloud: Any, target: str) -> Dict[str, Any]:
        base = super().evaluate_blast_radius(cloud, target)
        blast_limit = int(os.getenv("AUTO_REMEDIATE_BLAST_LIMIT", "2"))
        if target == "order-service":
            base["risk_level"] = "HIGH"
            base["safe_to_proceed"] = base["dependent_count"] <= blast_limit
            if not base["safe_to_proceed"]:
                base["safety_rationale"].append(
                    f"BLOCKED: {base['dependent_count']} dependents exceed auto-remediate limit ({blast_limit})."
                )
        elif target == "payment-gateway":
            base["risk_level"] = "MEDIUM"
        else:
            base["risk_level"] = "LOW"
        return base


class RollbackConfigPlugin(RemediationPlugin):
    """Reverts service configuration or deployment tag to the last known good baseline."""
    action_name: str = "rollback_config"
    description: str = "Rolls back service config/deployment to stable baseline"
    risk_level: str = "LOW"
    allowed_services: List[str] = ["api-gateway", "order-service", "payment-gateway", "inventory-worker"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        target_version = parameters.get("target_version", "previous")
        return cloud.rollback_service_config(service_name=target, target_version=target_version)


class ScaleServicePlugin(RemediationPlugin):
    """Adjusts replica count for auto-scaling groups / container services."""
    action_name: str = "scale_service"
    description: str = "Adjusts replica count to handle traffic spikes or drain backlogs"
    risk_level: str = "LOW"
    allowed_services: List[str] = ["inventory-worker", "payment-gateway", "order-service", "api-gateway"]
    max_scale_delta: int = 5

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        delta = int(parameters.get("delta", 1))
        return cloud.scale_service_instances(service_name=target, delta=delta)


class DrainTrafficPlugin(RemediationPlugin):
    """Gracefully stops new connections and drains active in-flight requests."""
    action_name: str = "drain_traffic"
    description: str = "Drains active traffic gracefully and notifies upstream callers"
    risk_level: str = "MEDIUM"
    allowed_services: List[str] = ["order-service", "payment-gateway", "api-gateway", "inventory-worker"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return cloud.drain_service_traffic(service_name=target)


class FlushCachePlugin(RemediationPlugin):
    """Flushes stale Redis / ElastiCache keys causing state or serialization errors."""
    action_name: str = "flush_cache"
    description: str = "Flushes stale cache keys from Redis/ElastiCache clusters"
    risk_level: str = "LOW"
    allowed_services: List[str] = ["redis-cluster", "session-cache", "catalog-cache", "*"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        key_pattern = parameters.get("key_pattern", "*")
        return cloud.flush_cache(cache_cluster=target, key_pattern=key_pattern)


class TripCircuitBreakerPlugin(RemediationPlugin):
    """Temporarily trips a circuit breaker to shed load from degraded third-party backends."""
    action_name: str = "trip_circuit_breaker"
    description: str = "Opens a circuit breaker to isolate degraded third-party dependencies"
    risk_level: str = "MEDIUM"
    allowed_services: List[str] = ["payment-gateway", "shipping-partner", "email-service", "*"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        shed_pct = int(parameters.get("shed_pct", 100))
        return cloud.trip_circuit_breaker(service_name=target, shed_pct=shed_pct)


class RerouteTrafficPlugin(RemediationPlugin):
    """Shifts traffic away from an impaired AWS Availability Zone or region."""
    action_name: str = "reroute_traffic"
    description: str = "Shifts incoming traffic away from an impaired Availability Zone"
    risk_level: str = "HIGH"
    allowed_services: List[str] = ["api-gateway", "ingress-alb", "*"]

    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        from_az = parameters.get("from_az", "us-east-1a")
        to_az = parameters.get("to_az", "us-east-1b")
        return cloud.reroute_traffic(service_name=target, from_az=from_az, to_az=to_az)
