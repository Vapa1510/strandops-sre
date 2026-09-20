"""StrandsOps Coordinator Agent — Autonomous Cloud SRE Agent.

Built with the Strands Agents SDK.
This coordinator acts like an experienced on-call engineer:
1. Observes raw telemetry and correlates error spikes.
2. Digs into stack traces to find the actual root cause (not just surface symptoms).
3. Evaluates the blast radius before taking action so it doesn't cause a cascading failure.
4. Executes targeted remediation (quarantine, restart, rollback).
5. Double-checks live metrics (closed loop) before closing the ticket.
6. Writes a clean postmortem report for the team.
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# System prompt modeled after real-world SRE on-call playbooks
SRE_SYSTEM_PROMPT = """
You are StrandsOps, an autonomous Site Reliability Engineering (SRE) assistant.
Your job is to triage cloud alerts, find root causes, execute safe self-healing actions,
and mathematically verify that systems have recovered before closing tickets.

Think like a seasoned on-call engineer:
- Rule #1: "First, do no harm." Never restart a service or purge data blindly.
- Rule #2: Always diagnose before acting. Check telemetry and logs first to know what broke.
- Rule #3: Check the blast radius. If restarting a service will drop upstream traffic, know the risks.
- Rule #4: Never trust a blind confirmation. Always re-probe telemetry to ensure error rate = 0.0%.
- Rule #5: Document everything. Once recovered, write an incident postmortem for the team.

Available Tools:
1. inspect_telemetry: Pull real-time P50/P95/P99 latency, error rates, RPS, and memory.
2. fetch_error_logs: Read recent error logs and stack traces from microservices.
3. inspect_queue_health: Inspect SQS message backlogs, dead-letter count, and poison pill IDs.
4. analyze_blast_radius: Mandatory safety check to evaluate dependency risks before remediation.
5. execute_remediation: Run safe operational primitives:
   - 'quarantine_messages' (isolate corrupted messages to DLQ)
   - 'restart_service' (graceful container reboot for memory/pool leaks)
   - 'rollback_config' (revert bad deployment to last stable version)
   - 'scale_service' (adjust instance count to handle load spikes, use parameters_json: {"delta": N})
   - 'drain_traffic' (gracefully stop new requests for maintenance)
6. verify_system_recovery: Closed-loop check with soak-window verification.
   Use soak_checks=3 for production incidents to catch flapping services.
7. generate_incident_postmortem: Output an executive Markdown postmortem summarizing the incident.

Communication:
Be clear, concise, and structured. Use emoji indicators for clarity:
- 🚨 Incident Detected
- 🔍 Root Cause Isolated
- 🛡️ Blast Radius Checked
- ⚡ Remediation Executed
- ✅ Closed-Loop Recovery Verified
"""


def get_provider_info() -> dict:
    """Return active model provider configuration and AWS Bedrock status."""
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20240620-v1:0")
    triage_model_id = os.getenv("BEDROCK_TRIAGE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    region = os.getenv("AWS_REGION", "us-east-1")
    has_keys = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    
    return {
        "provider": provider,
        "model_id": model_id,
        "triage_model_id": triage_model_id,
        "region": region,
        "has_credentials": has_keys,
        "status": "Connected (Amazon Bedrock Active)" if has_keys else "AWS Bedrock Configured (Awaiting Keys)",
        "inference_tier": "Two-Tier (Haiku Triage → Sonnet Reasoning)" if has_keys else "Single-Tier",
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
            sys.exit(1)

    elif provider == "anthropic":
        try:
            from strands.models.anthropic import AnthropicModel
            model_id = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
            return AnthropicModel(model_id=model_id)
        except ImportError:
            print("[WARN] Anthropic dependencies not found. Install with: pip install 'strands-agents[anthropic]'")
            sys.exit(1)

    elif provider == "ollama":
        try:
            from strands.models.ollama import OllamaModel
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model_id = os.getenv("OLLAMA_MODEL", "llama3.1")
            return OllamaModel(host=host, model_id=model_id)
        except ImportError:
            print("[WARN] Ollama dependencies not found. Install with: pip install 'strands-agents[ollama]'")
            sys.exit(1)

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


def create_sre_agent():
    """Initializes and returns the configured StrandsOps SRE Agent."""
    from strands import Agent
    from strandops.tools import SRE_TOOLS

    model = _build_model()
    kwargs = {
        "system_prompt": SRE_SYSTEM_PROMPT,
        "tools": SRE_TOOLS,
    }
    if model is not None:
        kwargs["model"] = model

    return Agent(**kwargs)
