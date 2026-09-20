"""Domain models for the StrandsOps cloud infrastructure simulator.

These models represent microservices, AWS SQS queues, telemetry metrics,
and incident state machines.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ServiceHealth(str, Enum):
    """Operational health status of a cloud service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class ChaosScenario(str, Enum):
    """Realistic production failure scenarios."""
    SQS_POISON_PILL = "sqs_poison_pill"
    MEMORY_LEAK_OOM = "memory_leak_oom"
    RATE_LIMIT_MISCONFIG = "rate_limit_misconfig"
    DB_CONNECTION_STARVATION = "db_connection_starvation"


class MetricSnapshot(BaseModel):
    """Point-in-time telemetry snapshot for a microservice."""
    service_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate_pct: float
    requests_per_sec: float
    memory_usage_mb: float
    cpu_usage_pct: float
    status: ServiceHealth


class QueueState(BaseModel):
    """State of an AWS SQS queue."""
    queue_name: str
    approximate_messages_visible: int
    approximate_messages_not_visible: int
    approximate_messages_delayed: int
    dead_letter_queue_name: Optional[str] = None
    dead_letter_count: int = 0
    poison_pill_ids: List[str] = Field(default_factory=list)


class LogSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class StructuredLog(BaseModel):
    """Structured JSON log entry emitted by cloud services."""
    timestamp: str
    service: str
    level: LogSeverity
    trace_id: str
    message: str
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IncidentSeverity(str, Enum):
    SEV1 = "SEV1"  # Catastrophic customer impact
    SEV2 = "SEV2"  # Degraded performance, core feature impacted
    SEV3 = "SEV3"  # Minor degradation, internal service warning


class IncidentStatus(str, Enum):
    """Lifecycle status of an active incident."""
    OPEN = "OPEN"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"


class IncidentRecord(BaseModel):
    """Active incident record tracked by the SRE agent."""
    incident_id: str
    title: str
    severity: IncidentSeverity
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    affected_services: List[str]
    root_cause_summary: Optional[str] = None
    remediation_actions_taken: List[str] = Field(default_factory=list)
    status: IncidentStatus = IncidentStatus.OPEN
