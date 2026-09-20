"""Shared SLA thresholds for telemetry and recovery checks.

Reads from env so dashboard, tools, and verification stay consistent.
Defaults match .env.example: P99 ≤ 120 ms, error rate ≤ 1.0%.
"""
from __future__ import annotations

import os


def max_p99_latency_ms() -> float:
    try:
        return float(os.getenv("SLA_MAX_P99_LATENCY_MS", "120"))
    except (TypeError, ValueError):
        return 120.0


def max_error_rate_pct() -> float:
    try:
        return float(os.getenv("SLA_MAX_ERROR_RATE_PERCENT", "1.0"))
    except (TypeError, ValueError):
        return 1.0


def is_sla_breached(error_rate_pct: float, p99_latency_ms: float) -> bool:
    return (error_rate_pct > max_error_rate_pct()) or (p99_latency_ms > max_p99_latency_ms())
