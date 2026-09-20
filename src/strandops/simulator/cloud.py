"""In-Process Cloud Infrastructure Simulator for StrandsOps.

Why an in-process simulator instead of LocalStack or Docker?
-----------------------------------------------------------
During hackathon testing, we found that running Docker/LocalStack on developer laptops
(especially Windows) introduced constant friction: daemon crashes, 10-minute cold starts,
and port conflicts.

This module provides a lightweight, event-driven in-process simulator that models:
- Microservices: api-gateway, order-service, payment-gateway, inventory-worker
- Messaging: SQS queue (order-processing-queue) with Dead-Letter Queue (DLQ)
- Real-time telemetry: P50/P95/P99 latency, error rates, RPS, and memory profiles
- Real-world failure modes: poison pills, connection leaks, bad deployments
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from strandops.simulator.models import (
    ChaosScenario,
    IncidentRecord,
    IncidentSeverity,
    LogSeverity,
    MetricSnapshot,
    QueueState,
    ServiceHealth,
    StructuredLog,
)
from strandops.simulator.provider import CloudProvider


def _normalize_name(name: Optional[str]) -> str:
    """Normalize service or queue name (strip, lower, convert spaces and underscores to hyphens)."""
    if not name:
        return ""
    return name.strip().lower().replace(" ", "-").replace("_", "-")


class CloudInfrastructure(CloudProvider):
    """Simulated cloud environment with realistic microservice topology and chaos injection."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset the simulated cluster to a pristine, healthy baseline."""
        self.active_incident: Optional[IncidentRecord] = None
        self.active_chaos: Optional[ChaosScenario] = None

        # Base microservice configurations
        self.service_configs = {
            "api-gateway": {"version": "v1.8.2", "rate_limit_rps": 500, "status": "running"},
            "order-service": {"version": "v2.4.0", "db_pool_size": 50, "status": "running"},
            "payment-gateway": {"version": "v3.1.1", "conn_pool_limit": 100, "status": "running"},
            "inventory-worker": {"version": "v1.2.0", "concurrency": 8, "status": "running"},
        }

        # Dependency graph (caller -> dependencies) used by the blast radius safety tool
        self.dependencies = {
            "api-gateway": ["order-service"],
            "order-service": ["payment-gateway", "order-processing-queue"],
            "inventory-worker": ["order-processing-queue"],
            "payment-gateway": [],
        }

        # Per-service instance counts (used by scale_service primitive)
        self.instance_counts = {
            "api-gateway": 2,
            "order-service": 3,
            "payment-gateway": 2,
            "inventory-worker": 2,
        }

        # Per-service traffic draining state
        self.draining_services: List[str] = []

        # SQS Queue state
        self.queue = QueueState(
            queue_name="order-processing-queue",
            approximate_messages_visible=12,
            approximate_messages_not_visible=2,
            approximate_messages_delayed=0,
            dead_letter_queue_name="order-processing-dlq",
            dead_letter_count=0,
            poison_pill_ids=[],
        )

        # In-memory structured log ring buffer
        self.logs: List[StructuredLog] = []
        self._emit_log("api-gateway", LogSeverity.INFO, "API Gateway initialized on port 8080 (healthy)")
        self._emit_log("order-service", LogSeverity.INFO, "Database connection pool established (50/50 ready)")
        self._emit_log("payment-gateway", LogSeverity.INFO, "Payment vault integration active")
        self._emit_log("inventory-worker", LogSeverity.INFO, "Worker polling SQS queue 'order-processing-queue'")

    def _emit_log(
        self,
        service: str,
        level: LogSeverity,
        message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StructuredLog:
        entry = StructuredLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            service=service,
            level=level,
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            message=message,
            error_type=error_type,
            stack_trace=stack_trace,
            metadata=metadata or {},
        )
        self.logs.append(entry)
        # Keep ring buffer manageable
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        return entry

    # =========================================================================
    # Chaos Injection Engine (Simulating Messy Production Outages)
    # =========================================================================

    def inject_chaos(self, scenario: ChaosScenario) -> IncidentRecord:
        """Injects a realistic production failure scenario for the agent to triage."""
        self.active_chaos = scenario
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"

        if scenario == ChaosScenario.SQS_POISON_PILL:
            # Scenario A: 3 malformed JSON payloads hit the queue.
            # Worker threads crash trying to parse them, causing a retry storm
            # and backlogging hundreds of valid customer orders.
            poison_ids = ["msg-bad-881", "msg-bad-882", "msg-bad-883"]
            self.queue.approximate_messages_visible = 450
            self.queue.dead_letter_count = 18
            self.queue.poison_pill_ids = poison_ids

            self.active_incident = IncidentRecord(
                incident_id=incident_id,
                title="SQS Poison Pill Storm — Inventory Worker Crashing",
                severity=IncidentSeverity.SEV1,
                affected_services=["inventory-worker", "order-processing-queue"],
            )

            for pid in poison_ids:
                self._emit_log(
                    service="inventory-worker",
                    level=LogSeverity.ERROR,
                    message=f"Failed to parse order payload for message ID {pid}",
                    error_type="json.decoder.JSONDecodeError",
                    stack_trace=(
                        f"Traceback (most recent call last):\n"
                        f"  File 'worker/consumer.py', line 112, in process_message\n"
                        f"    order_data = json.loads(raw_body)\n"
                        f"  File '/usr/lib/python3.11/json/__init__.py', line 346, in loads\n"
                        f"json.decoder.JSONDecodeError: Unterminated string starting at line 1 column 48\n"
                        f"Corrupted Message ID: {pid}"
                    ),
                    metadata={"message_id": pid, "queue": "order-processing-queue"},
                )

        elif scenario == ChaosScenario.MEMORY_LEAK_OOM:
            # Scenario B: Unclosed HTTP connection pool in payment client.
            # Connection pool exhausts, memory climbs to 1940MB / 2048MB,
            # and P99 latency degrades to 3,450ms, throwing 504 Gateway Timeouts.
            self.active_incident = IncidentRecord(
                incident_id=incident_id,
                title="Payment Gateway Memory Leak & Latency Degradation",
                severity=IncidentSeverity.SEV1,
                affected_services=["payment-gateway", "order-service"],
            )

            self._emit_log(
                service="payment-gateway",
                level=LogSeverity.ERROR,
                message="ResourceExhaustion: Unclosed HTTP connection pool in Stripe client (980/1000 open)",
                error_type="ConnectionPoolTimeout",
                stack_trace=(
                    "Traceback (most recent call last):\n"
                    "  File 'clients/payment_client.py', line 89, in execute_charge\n"
                    "    response = await session.post('/v1/charges', timeout=3.0)\n"
                    "urllib3.exceptions.MaxRetryError: Connection pool is full, discarding connection"
                ),
                metadata={"memory_mb": "1940", "max_memory_mb": "2048"},
            )

        elif scenario == ChaosScenario.RATE_LIMIT_MISCONFIG:
            # Scenario C: A Friday afternoon deployment botched the rate limiter
            # setting max_rps=5 instead of 500, rejecting 88% of user traffic.
            self.service_configs["api-gateway"]["rate_limit_rps"] = 5
            self.service_configs["api-gateway"]["version"] = "v1.8.3-bad"

            self.active_incident = IncidentRecord(
                incident_id=incident_id,
                title="API Gateway Misconfigured Rate Limiting (v1.8.3)",
                severity=IncidentSeverity.SEV1,
                affected_services=["api-gateway"],
            )

            self._emit_log(
                service="api-gateway",
                level=LogSeverity.WARN,
                message="Rate limit exceeded: 429 Too Many Requests sent to client. Configured limit: 5 RPS",
                error_type="HTTP_429_TOO_MANY_REQUESTS",
                metadata={"applied_limit": "5", "current_demand": "180"},
            )

        elif scenario == ChaosScenario.DB_CONNECTION_STARVATION:
            # Scenario D: Database connection pool deadlock in order-service.
            self.active_incident = IncidentRecord(
                incident_id=incident_id,
                title="Database Connection Pool Starvation in Order Service",
                severity=IncidentSeverity.SEV2,
                affected_services=["order-service"],
            )

            self._emit_log(
                service="order-service",
                level=LogSeverity.ERROR,
                message="Timeout acquiring connection from pool (50/50 connections active, 120 waiting)",
                error_type="PoolTimeoutError",
                stack_trace=(
                    "sqlalchemy.exc.TimeoutError: QueuePool limit of size 50 overflow 10 reached, "
                    "connection timed out, timeout 10.00"
                ),
            )

        return self.active_incident

    # =========================================================================
    # Telemetry & Observability
    # =========================================================================

    def get_telemetry(self, service_name: Optional[str] = None) -> List[MetricSnapshot]:
        """Calculates point-in-time metrics based on current cluster state."""
        snapshots = []
        normalized_target = _normalize_name(service_name) if service_name else None
        services = [normalized_target] if normalized_target else list(self.service_configs.keys())

        for svc in services:
            if svc not in self.service_configs:
                continue

            # Standard healthy operational baselines
            p50 = 18.0
            p95 = 38.0
            p99 = 48.0
            err_rate = 0.0
            rps = 145.0
            mem = 220.0
            cpu = 14.5
            health = ServiceHealth.HEALTHY

            # Apply incident degradation dynamically
            if self.active_chaos == ChaosScenario.SQS_POISON_PILL and svc == "inventory-worker":
                err_rate = 84.5
                p99 = 480.0
                health = ServiceHealth.CRITICAL
            elif self.active_chaos == ChaosScenario.MEMORY_LEAK_OOM:
                if svc == "payment-gateway":
                    p50 = 1200.0
                    p95 = 2800.0
                    p99 = 3450.0
                    err_rate = 42.0
                    mem = 1940.0
                    cpu = 88.0
                    health = ServiceHealth.CRITICAL
                elif svc == "order-service":
                    p99 = 3500.0
                    err_rate = 38.0
                    health = ServiceHealth.DEGRADED
            elif self.active_chaos == ChaosScenario.RATE_LIMIT_MISCONFIG and svc == "api-gateway":
                err_rate = 89.2
                p99 = 62.0
                health = ServiceHealth.CRITICAL
            elif self.active_chaos == ChaosScenario.DB_CONNECTION_STARVATION and svc == "order-service":
                p99 = 1800.0
                err_rate = 68.0
                health = ServiceHealth.CRITICAL

            # If traffic is being drained from this service, reflect 0 RPS
            if svc in self.draining_services:
                rps = 0.0
                if health == ServiceHealth.HEALTHY:
                    health = ServiceHealth.DEGRADED

            snapshots.append(
                MetricSnapshot(
                    service_name=svc,
                    p50_latency_ms=p50,
                    p95_latency_ms=p95,
                    p99_latency_ms=p99,
                    error_rate_pct=err_rate,
                    requests_per_sec=rps,
                    memory_usage_mb=mem,
                    cpu_usage_pct=cpu,
                    status=health,
                )
            )

        return snapshots

    def get_logs(self, service_name: Optional[str] = None, limit: int = 20) -> List[StructuredLog]:
        """Fetch structured log stream filtered by service."""
        target = _normalize_name(service_name) if service_name else None
        filtered = [l for l in self.logs if (target is None or l.service == target)]
        return filtered[-limit:]

    def get_queue_state(self) -> QueueState:
        """Returns the current SQS queue state and DLQ counters."""
        return self.queue

    def get_topology(self) -> Dict[str, List[str]]:
        """Returns the service dependency map for blast radius checking."""
        return self.dependencies

    # =========================================================================
    # Safe Remediation Primitives
    # =========================================================================

    def quarantine_queue_messages(self, queue_name: str, message_ids: List[str]) -> Dict[str, object]:
        """Moves corrupted poison pill messages to the DLQ to unblock processing."""
        normalized_q = _normalize_name(queue_name)
        if _normalize_name(self.queue.queue_name) != normalized_q:
            return {"status": "error", "reason": f"Unknown queue '{queue_name}'"}

        quarantined = []
        # Copy message_ids list to prevent mutation during iteration
        for mid in list(message_ids):
            if mid in self.queue.poison_pill_ids:
                self.queue.poison_pill_ids.remove(mid)
                quarantined.append(mid)
                self.queue.dead_letter_count += 1

        # When all poison pills are isolated, the queue and workers recover
        if not self.queue.poison_pill_ids:
            self.queue.approximate_messages_visible = 4
            self.active_chaos = None
            if self.active_incident:
                self.active_incident.status = "RESOLVED"
                self.active_incident.resolved_at = datetime.now(timezone.utc)
                self.active_incident.remediation_actions_taken.append(
                    f"Quarantined {len(quarantined)} poison messages to DLQ: {', '.join(quarantined)}"
                )

        self._emit_log(
            service="inventory-worker",
            level=LogSeverity.INFO,
            message=f"Quarantined {len(quarantined)} poison pill(s) to {self.queue.dead_letter_queue_name}: {quarantined}",
        )

        return {
            "status": "success",
            "quarantined_count": len(quarantined),
            "quarantined_ids": quarantined,
            "queue_backlog_remaining": self.queue.approximate_messages_visible,
        }

    def restart_service_instance(self, service_name: str) -> Dict[str, object]:
        """Gracefully reboots a microservice container, flushing leaked memory and hung pools."""
        svc = _normalize_name(service_name)
        if svc not in self.service_configs:
            return {"status": "error", "reason": f"Unknown service '{service_name}'"}

        self._emit_log(
            service=svc,
            level=LogSeverity.INFO,
            message=f"Gracefully rebooting container instance for '{svc}'",
        )

        # Resolves memory leaks and pool exhaustion
        if self.active_chaos == ChaosScenario.MEMORY_LEAK_OOM and svc == "payment-gateway":
            self.active_chaos = None
            if self.active_incident:
                self.active_incident.status = "RESOLVED"
                self.active_incident.resolved_at = datetime.now(timezone.utc)
                self.active_incident.remediation_actions_taken.append(
                    f"Restarted '{svc}' container; reset memory pool and flushed unclosed HTTP connections."
                )
        elif self.active_chaos == ChaosScenario.DB_CONNECTION_STARVATION and svc == "order-service":
            self.active_chaos = None
            if self.active_incident:
                self.active_incident.status = "RESOLVED"
                self.active_incident.resolved_at = datetime.now(timezone.utc)
                self.active_incident.remediation_actions_taken.append(
                    f"Restarted '{svc}' container; flushed hung database transactions and reset connection pool (50/50 ready)."
                )

        self._emit_log(
            service=svc,
            level=LogSeverity.INFO,
            message=f"Service '{svc}' restarted successfully. Memory: 215MB, Connections: 0/100",
        )

        return {
            "status": "success",
            "service": svc,
            "restarted_at": datetime.now(timezone.utc).isoformat(),
            "new_state": "running (healthy)",
        }

    def rollback_service_config(self, service_name: str, target_version: str = "previous") -> Dict[str, object]:
        """Rolls back a service configuration or deployment tag to the last known good baseline."""
        svc = _normalize_name(service_name)
        if svc not in self.service_configs:
            return {"status": "error", "reason": f"Unknown service '{service_name}'"}

        if self.active_chaos == ChaosScenario.RATE_LIMIT_MISCONFIG and svc == "api-gateway":
            self.service_configs["api-gateway"]["rate_limit_rps"] = 500
            self.service_configs["api-gateway"]["version"] = "v1.8.2"
            self.active_chaos = None
            if self.active_incident:
                self.active_incident.status = "RESOLVED"
                self.active_incident.resolved_at = datetime.now(timezone.utc)
                self.active_incident.remediation_actions_taken.append(
                    f"Rolled back {svc} from v1.8.3 to v1.8.2; restored rate_limit_rps=500"
                )

        self._emit_log(
            service=svc,
            level=LogSeverity.INFO,
            message=f"Config rolled back to stable baseline on {svc}. Rate limits restored.",
        )

        return {
            "status": "success",
            "service": svc,
            "active_version": self.service_configs[svc]["version"],
            "restored_config": self.service_configs[svc],
        }

    def scale_service_instances(self, service_name: str, delta: int) -> Dict[str, object]:
        """Scale up or down the number of running instances for a service.

        Safety guardrails:
        - Maximum delta of ±5 instances per operation (prevents runaway scaling).
        - Instance count is clamped to [1, 10] — never scales to zero (preserves availability)
          and never exceeds 10 (prevents cost blowouts).
        """
        svc = _normalize_name(service_name)
        if svc not in self.service_configs:
            return {"status": "error", "reason": f"Unknown service '{service_name}'"}

        max_delta = int(os.getenv("MAX_SCALE_DELTA", "5"))
        clamped_delta = max(-max_delta, min(delta, max_delta))

        old_count = self.instance_counts.get(svc, 2)
        new_count = max(1, min(old_count + clamped_delta, 10))
        self.instance_counts[svc] = new_count

        if self.active_incident:
            self.active_incident.remediation_actions_taken.append(
                f"Scaled '{svc}' instances from {old_count} to {new_count} (delta: {clamped_delta:+d})"
            )

        self._emit_log(
            service=svc,
            level=LogSeverity.INFO,
            message=f"Scaled {svc} from {old_count} to {new_count} instances (delta: {clamped_delta:+d})",
        )

        return {
            "status": "success",
            "service": svc,
            "previous_count": old_count,
            "new_count": new_count,
            "delta_applied": clamped_delta,
            "delta_requested": delta,
            "clamped": delta != clamped_delta,
            "scaled_at": datetime.now(timezone.utc).isoformat(),
        }

    def drain_service_traffic(self, service_name: str) -> Dict[str, object]:
        """Drain active connections from a service and redirect traffic to healthy peers.

        This is a non-destructive operation — the service keeps running but stops
        receiving new requests, allowing in-flight requests to complete gracefully.
        Useful before performing maintenance or investigating intermittent failures.
        """
        svc = _normalize_name(service_name)
        if svc not in self.service_configs:
            return {"status": "error", "reason": f"Unknown service '{service_name}'"}

        if svc in self.draining_services:
            return {
                "status": "already_draining",
                "service": svc,
                "message": f"Traffic to {svc} is already being drained.",
            }

        self.draining_services.append(svc)

        # Identify peers that will absorb the redirected traffic
        dependents = [s for s, deps in self.dependencies.items() if svc in deps]

        if self.active_incident:
            self.active_incident.remediation_actions_taken.append(
                f"Drained traffic from '{svc}' gracefully (redirecting upstream callers: {', '.join(dependents) or 'none'})"
            )

        self._emit_log(
            service=svc,
            level=LogSeverity.INFO,
            message=f"Draining traffic from {svc}. In-flight requests completing gracefully. "
                    f"Upstream callers ({', '.join(dependents) or 'none'}) redirecting to healthy peers.",
        )

        return {
            "status": "success",
            "service": svc,
            "traffic_state": "draining",
            "upstream_callers_notified": dependents,
            "drained_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton cloud instance — resolved via the provider factory
cloud = CloudInfrastructure()
