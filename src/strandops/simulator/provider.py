"""Abstract Cloud Provider Interface for StrandsOps.

Defines the contract that any cloud backend (simulated or live AWS) must implement.
This allows the SRE agent's tools to work identically regardless of whether
they're running against an in-process simulator or a real AWS account.

To switch backends, set the CLOUD_BACKEND environment variable:
    CLOUD_BACKEND=simulator   (default — zero-setup local testing)
    CLOUD_BACKEND=aws         (live AWS CloudWatch, ECS, SQS — requires credentials)
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from strandops.simulator.models import (
    ChaosScenario,
    IncidentRecord,
    MetricSnapshot,
    QueueState,
    StructuredLog,
)


class CloudProvider(ABC):
    """Abstract base class for cloud infrastructure backends.

    Every tool in strandops.tools imports `cloud` and calls methods on it.
    By coding against this interface, we can swap the in-process simulator
    for a live AWS adapter (CloudWatch + ECS + SQS) without changing any
    tool code — only the provider implementation changes.
    """

    # State that all providers must expose
    active_incident: Optional[IncidentRecord]
    active_chaos: Optional[ChaosScenario]

    @abstractmethod
    def reset(self) -> None:
        """Reset the cloud environment to a clean, healthy baseline."""
        ...

    # ── Observability ────────────────────────────────────────────────────

    @abstractmethod
    def get_telemetry(self, service_name: Optional[str] = None) -> List[MetricSnapshot]:
        """Return point-in-time telemetry for one or all services."""
        ...

    @abstractmethod
    def get_logs(self, service_name: Optional[str] = None, limit: int = 20) -> List[StructuredLog]:
        """Return recent structured log entries, optionally filtered by service."""
        ...

    @abstractmethod
    def get_queue_state(self) -> QueueState:
        """Return the current SQS queue state and DLQ counters."""
        ...

    @abstractmethod
    def get_topology(self) -> Dict[str, List[str]]:
        """Return the service dependency graph (caller -> [dependencies])."""
        ...

    # ── Remediation Primitives ───────────────────────────────────────────

    @abstractmethod
    def quarantine_queue_messages(self, queue_name: str, message_ids: List[str]) -> Dict[str, object]:
        """Move corrupted messages to the dead-letter queue."""
        ...

    @abstractmethod
    def restart_service_instance(self, service_name: str) -> Dict[str, object]:
        """Gracefully reboot a service container."""
        ...

    @abstractmethod
    def rollback_service_config(self, service_name: str, target_version: str = "previous") -> Dict[str, object]:
        """Revert a service to its last known good configuration."""
        ...

    @abstractmethod
    def scale_service_instances(self, service_name: str, delta: int) -> Dict[str, object]:
        """Scale up or down the number of service instances."""
        ...

    @abstractmethod
    def drain_service_traffic(self, service_name: str) -> Dict[str, object]:
        """Drain active connections from a service and redirect to peers."""
        ...

    @abstractmethod
    def flush_cache(self, cache_cluster: str, key_pattern: str = "*") -> Dict[str, object]:
        """Flush keys from a cache cluster (Redis/ElastiCache)."""
        ...

    @abstractmethod
    def trip_circuit_breaker(self, service_name: str, shed_pct: int = 100) -> Dict[str, object]:
        """Trip a circuit breaker to isolate degraded third-party backends."""
        ...

    @abstractmethod
    def reroute_traffic(self, service_name: str, from_az: str, to_az: str) -> Dict[str, object]:
        """Shift traffic away from an impaired Availability Zone."""
        ...

    # ── Chaos Engineering (simulator-only, no-op on live) ────────────────

    def inject_chaos(self, scenario: ChaosScenario) -> IncidentRecord:
        """Inject a failure scenario. Only meaningful for simulated backends."""
        raise NotImplementedError("Chaos injection is only available on the simulated backend.")


_provider_instance: Optional[CloudProvider] = None


def reset_cloud_provider_cache() -> None:
    """Clear the cached provider so the next get_cloud_provider() re-reads CLOUD_BACKEND."""
    global _provider_instance
    _provider_instance = None


def get_cloud_provider() -> CloudProvider:
    """Factory that returns the configured cloud backend singleton.

    Reads CLOUD_BACKEND from the environment:
        'simulator' (default) — in-process event-driven simulator
        'aws'                 — live AWS CloudWatch / ECS / SQS adapter
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    backend = os.getenv("CLOUD_BACKEND", "simulator").lower()

    if backend == "aws":
        from strandops.simulator.aws_provider import LiveAWSProvider
        _provider_instance = LiveAWSProvider()
        return _provider_instance

    # Default: canonical in-process simulator singleton
    from strandops.simulator.cloud import cloud as simulator_cloud
    _provider_instance = simulator_cloud
    return _provider_instance
