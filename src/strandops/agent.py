"""StrandsOps coordinator — on-call helper for cloud incidents.

Investigates alerts, finds root causes, checks blast radius before acting,
applies a targeted fix, re-checks metrics, then writes a short postmortem.
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def _build_system_prompt() -> str:
    """System prompt with live SLA thresholds from env / sla helpers."""
    from strandops.sla import max_error_rate_pct, max_p99_latency_ms

    sla_err = max_error_rate_pct()
    sla_p99 = max_p99_latency_ms()
    return f"""
You are StrandsOps, an on-call SRE helper for this cluster.
Triage alerts, find root causes, apply safe fixes, and verify recovery
before closing the ticket - like a careful junior engineer on page duty.

Rules:
1. Do no harm. Never restart a service or purge data blindly.
2. Diagnose first. Read telemetry and logs before changing anything.
3. Check blast radius. Know who else feels a restart or rollback.
4. Do not trust a blind "done." Re-check telemetry: error rate <= {sla_err}%
   and P99 <= {sla_p99} ms across the soak window before calling it recovered.
5. Write it down. Leave a short postmortem once things are stable.

Tools:
1. inspect_telemetry - P50/P95/P99 latency, error rates, RPS, memory
2. fetch_error_logs - recent WARN/ERROR/FATAL logs and stack traces
3. inspect_queue_health - SQS backlog, DLQ count, poison pill IDs
4. analyze_blast_radius - required before any mutating remediation
5. execute_remediation - bounded actions only:
   - quarantine_messages (move bad messages to DLQ)
   - restart_service (graceful reboot for memory/pool leaks)
   - rollback_config (revert a bad deploy)
   - scale_service (parameters_json: {{"delta": N}})
   - drain_traffic (stop new requests for maintenance)
6. verify_system_recovery - soak-window check; use soak_checks=3 for real incidents
7. generate_incident_postmortem - short Markdown write-up for leadership

How to talk:
Be plain and specific. Prefer short sections over slogans.
Skip marketing language ("autonomous", "AI agent", "self-healing").
Say what you saw, what you did, and what the metrics say now.
"""


SRE_SYSTEM_PROMPT = _build_system_prompt()


def get_provider_info() -> dict:
    """Return active model provider configuration and AWS Bedrock status."""
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    raw_account = os.getenv("AWS_ACCOUNT_ID", "379264687588").replace("-", "")
    formatted_account = f"{raw_account[:4]}-{raw_account[4:8]}-{raw_account[8:]}" if len(raw_account) == 12 else raw_account
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20240620-v1:0")
    triage_model_id = os.getenv("BEDROCK_TRIAGE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    region = os.getenv("AWS_REGION", "us-east-1")
    has_keys = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))

    return {
        "provider": provider,
        "account_id": formatted_account,
        "raw_account_id": raw_account,
        "model_id": model_id,
        "triage_model_id": triage_model_id,
        "region": region,
        "has_credentials": has_keys,
        "status": "Connected" if has_keys else "Waiting for AWS keys",
        "inference_tier": "Cache first, then full investigation" if has_keys else "Local / single path",
    }


def _build_model():
    """Configure the LLM provider.

    Defaults to Amazon Bedrock (Claude 3.5 Sonnet) to make best use of AWS credits,
    with flexible fallbacks to OpenAI, Anthropic direct, or local Ollama.
    """
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()

    if provider == "openai":
        try:
            from strands.models.openai import OpenAIModel
            model_id = os.getenv("OPENAI_MODEL", "gpt-4o")
            return OpenAIModel(model_id=model_id)
        except ImportError:
            print("[WARN] OpenAI dependencies not found. Install with: pip install 'strands-agents[openai]'")
            return None

    elif provider == "anthropic":
        try:
            from strands.models.anthropic import AnthropicModel
            model_id = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
            return AnthropicModel(model_id=model_id)
        except ImportError:
            print("[WARN] Anthropic dependencies not found. Install with: pip install 'strands-agents[anthropic]'")
            return None

    elif provider == "ollama":
        try:
            from strands.models.ollama import OllamaModel
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model_id = os.getenv("OLLAMA_MODEL", "llama3.1")
            return OllamaModel(host=host, model_id=model_id)
        except ImportError:
            print("[WARN] Ollama dependencies not found. Install with: pip install 'strands-agents[ollama]'")
            return None

    else:  # Default: Amazon Bedrock (Primary choice for the hackathon)
        try:
            import boto3
            from strands.models.bedrock import BedrockModel

            model_id = os.getenv(
                "BEDROCK_MODEL_ID",
                "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
            )
            region = os.getenv("AWS_REGION", "us-east-1")
            
            # Use explicit credentials if present in environment
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            session_token = os.getenv("AWS_SESSION_TOKEN")

            if access_key and secret_key:
                session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token,
                    region_name=region,
                )
                return BedrockModel(boto_session=session, model_id=model_id)
            else:
                return BedrockModel(model_id=model_id, region_name=region)

        except Exception as e:
            print(f"[INFO] Bedrock initialization note: {e}. Set AWS credentials in .env to use Bedrock.")
            return None


def _build_triage_model():
    """Build fast Tier-1 model (Haiku / Nova) for low-cost log parsing and classification."""
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    if provider == "bedrock":
        try:
            import boto3
            from strands.models.bedrock import BedrockModel

            model_id = os.getenv("BEDROCK_TRIAGE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
            region = os.getenv("AWS_REGION", "us-east-1")
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            session_token = os.getenv("AWS_SESSION_TOKEN")

            if access_key and secret_key:
                session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token,
                    region_name=region,
                )
                return BedrockModel(boto_session=session, model_id=model_id)
            else:
                return BedrockModel(model_id=model_id, region_name=region)
        except Exception:
            return None
    return None


def fast_triage_incident(service_name: str = "", error_type: str = "", signature: str = "") -> dict:
    """Check the playbook cache before a full investigation.

    If this exact failure was fixed and verified before, return that plan immediately.
    """
    from strandops.cache import incident_cache

    cached = incident_cache.lookup(
        service=service_name or "",
        error_type=error_type or "",
        signature=signature or "",
    )
    if cached:
        return {
            "tier": "playbook_hit",
            "escalation_needed": False,
            "cost_usd": 0.0,
            "latency_ms": cached["lookup_latency_ms"],
            "plan": cached["remediation_plan"],
        }

    return {
        "tier": "full_investigation",
        "escalation_needed": True,
        "escalate_to": "full_investigation",
        "reason": "No matching playbook for this signature yet.",
    }


def create_sre_agent():
    """Create the StrandsOps on-call helper with tools and model wiring."""
    from strands import Agent
    from strandops.tools import SRE_TOOLS

    model = _build_model()
    kwargs = {
        "system_prompt": _build_system_prompt(),
        "tools": SRE_TOOLS,
    }
    if model is not None:
        kwargs["model"] = model

    return Agent(**kwargs)
