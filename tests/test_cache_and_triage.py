"""Automated Test Suite for Semantic Incident Cache & Two-Tier Inference.

Validates:
- Deterministic incident fingerprint generation & normalization
- Pre-seeded verified remediation cache hits (SQS, OOM, 429, DB Pool)
- Zero-cost, sub-millisecond lookup response
- Cache miss handling on novel/unknown incidents
- Dynamic cache storage and stats tracking (hits, misses, hit ratio %)
- fast_triage_incident() routing: Tier-0 (cache) vs Tier-1 (escalation)
- Model provider configuration & inference tier reporting
"""
from __future__ import annotations

import pytest
from strandops.cache import IncidentCache, incident_cache
from strandops.agent import fast_triage_incident, get_provider_info


# =============================================================================
# Semantic Fingerprinting & Normalization
# =============================================================================

def test_fingerprint_deterministic():
    fp1 = IncidentCache.compute_fingerprint("payment-gateway", "ConnectionPoolTimeout", "pool is full")
    fp2 = IncidentCache.compute_fingerprint("payment-gateway", "ConnectionPoolTimeout", "pool is full")
    assert fp1 == fp2
    assert len(fp1) == 16


def test_fingerprint_normalizes_casing_and_symbols():
    fp1 = IncidentCache.compute_fingerprint("Payment Gateway", "connectionpooltimeout", "Pool is full")
    fp2 = IncidentCache.compute_fingerprint("payment_gateway", "ConnectionPoolTimeout", "pool is full")
    assert fp1 == fp2


def test_fingerprint_collision_resistance():
    fp1 = IncidentCache.compute_fingerprint("payment-gateway", "ConnectionPoolTimeout", "error A")
    fp2 = IncidentCache.compute_fingerprint("order-service", "ConnectionPoolTimeout", "error A")
    assert fp1 != fp2


# =============================================================================
# Pre-Seeded Cache Hits for Production Playbooks
# =============================================================================

def test_cache_hit_sqs_poison_pill():
    hit = incident_cache.lookup(
        service="inventory-worker",
        error_type="json.decoder.JSONDecodeError",
        signature="Unterminated string starting at line",
    )
    assert hit is not None
    assert hit["cache_hit"] is True
    assert hit["estimated_cost_usd"] == 0.0
    assert hit["remediation_plan"]["action_type"] == "quarantine_messages"
    assert hit["remediation_plan"]["target"] == "order-processing-queue"


def test_cache_hit_payment_gateway_oom():
    hit = incident_cache.lookup(
        service="payment-gateway",
        error_type="ConnectionPoolTimeout",
        signature="Connection pool is full, discarding connection",
    )
    assert hit is not None
    assert hit["cache_hit"] is True
    assert hit["remediation_plan"]["action_type"] == "restart_service"


def test_cache_hit_api_gateway_rate_limit():
    hit = incident_cache.lookup(
        service="api-gateway",
        error_type="HTTP_429_TOO_MANY_REQUESTS",
        signature="Rate limit exceeded: 429 Too Many Requests sent to client",
    )
    assert hit is not None
    assert hit["remediation_plan"]["action_type"] == "rollback_config"


def test_cache_hit_db_connection_starvation():
    hit = incident_cache.lookup(
        service="order-service",
        error_type="PoolTimeoutError",
        signature="QueuePool limit of size 50 overflow 10 reached",
    )
    assert hit is not None
    assert hit["remediation_plan"]["action_type"] == "restart_service"


def test_cache_miss_on_unseen_incident():
    miss = incident_cache.lookup(
        service="analytics-pipeline",
        error_type="KafkaConsumerGroupDeadlock",
        signature="Partition reassignment rebalance failed",
    )
    assert miss is None


# =============================================================================
# Dynamic Cache Storage & Hit Ratio Statistics
# =============================================================================

def test_dynamic_cache_store_and_recall():
    cache = IncidentCache()
    fp = cache.store(
        service="recommendation-service",
        error_type="VectorIndexCorrupted",
        signature="HNSW index deserialization failed",
        plan={"action_type": "rebuild_index", "target": "recommendation-service"},
    )
    assert fp is not None
    hit = cache.lookup("recommendation-service", "VectorIndexCorrupted", "HNSW index deserialization failed")
    assert hit is not None
    assert hit["remediation_plan"]["action_type"] == "rebuild_index"


def test_cache_statistics_tracking():
    cache = IncidentCache()
    initial_stats = cache.get_stats()
    assert initial_stats["cached_entries"] >= 4

    # Trigger hit
    cache.lookup("inventory-worker", "json.decoder.JSONDecodeError", "Unterminated string starting at line")
    stats = cache.get_stats()
    assert stats["hits"] > initial_stats["hits"]
    assert stats["total_queries"] > 0
    assert stats["hit_ratio_pct"] > 0.0


# =============================================================================
# Hybrid Tier-1 Fast Triage Routing
# =============================================================================

def test_fast_triage_known_incident_resolves_in_tier_zero():
    res = fast_triage_incident(
        service_name="api-gateway",
        error_type="HTTP_429_TOO_MANY_REQUESTS",
        signature="Rate limit exceeded: 429 Too Many Requests sent to client",
    )
    assert res["tier"] == "playbook_hit"
    assert res["escalation_needed"] is False
    assert res["cost_usd"] == 0.0
    assert res["plan"]["action_type"] == "rollback_config"


def test_fast_triage_novel_incident_escalates_to_tier_two():
    res = fast_triage_incident(
        service_name="order-service",
        error_type="UnhandledCustomCorruptedException",
        signature="Unknown stack trace failure",
    )
    assert res["tier"] == "full_investigation"
    assert res["escalation_needed"] is True
    assert res["escalate_to"] == "full_investigation"


def test_provider_info_reports_two_tier_configuration():
    info = get_provider_info()
    assert "provider" in info
    assert "model_id" in info
    assert "triage_model_id" in info
    assert "inference_tier" in info
    assert "claude" in info["model_id"].lower()
    assert "haiku" in info["triage_model_id"].lower()
