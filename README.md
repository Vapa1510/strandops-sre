# 🛡️ StrandsOps — The 3 AM On-Call AI Co-Pilot

> **An autonomous SRE agent built with the [Strands Agents SDK](https://strandsagents.com) that investigates alerts, isolates root causes, checks blast radius, and safely heals cloud microservices before your phone rings.**

Built for the **WeMakeDevs Bharat Builds / First Commit Hackathon 2026** — **BUILD IT Track (Agents & AI)**.

---

## The Story: Why We Built This

If you've ever been on-call, you know the exact feeling:
It’s 3:17 AM on a Sunday. PagerDuty starts blaring. You drag yourself out of bed, squinting at a bright screen with 12 Datadog and CloudWatch tabs open. You're half-asleep, heart racing, trying to figure out:
* *Did the payment gateway crash?*
* *Is there a poison pill in the SQS queue?*
* *Did someone push a bad deployment with broken rate limits on Friday afternoon?*

You’re terrified of running the wrong command because restarting a service blindly can trigger a thundering herd that knocks down your database.

According to Gartner, cloud downtime costs enterprises **\$5,600 every single minute**. But the real bottleneck isn't detection (alarms ring in seconds). The bottleneck is **Mean Time to Resolve (MTTR)**, which averages **45 to 90 minutes**—most of which is humans frantically sifting through logs and guessing.

We asked ourselves: **Can we build an autonomous agent using the Strands Agents SDK that acts like an experienced junior SRE? An agent that investigates alerts, diagnoses the root cause, checks the blast radius so it doesn't break production worse, applies the fix, and proves it worked?**

That is **StrandsOps**.

---

## What Makes This Different from Typical "AI Agents"?

Most hackathon AI agents are either chatbots that summarize text or dangerous scripts given raw bash access (`os.system`). In production, giving an LLM raw terminal access is a recipe for disaster.

StrandsOps is built on four core engineering principles:

1. **No Hallucinated Actions (Bounded Primitives):** The agent does not execute arbitrary shell scripts. It has strictly typed, safe operational primitives (`quarantine_messages`, `restart_service`, `rollback_config`, `scale_service`, `drain_traffic`).
2. **Mandatory Blast-Radius Gate:** Before touching any service, the agent evaluates the dependency graph. If restarting a service threatens upstream traffic, it flags the risk and blocks execution.
3. **Closed-Loop Soak-Window Verification (No False Victories):** Typical agents run a command, receive `200 OK`, and declare victory while the queue is still jammed. StrandsOps runs **multi-checkpoint soak verification** and detects "flapping" services that briefly recover before crashing again.
4. **Swappable Cloud Backend (Simulator ↔ Live AWS):** An abstract `CloudProvider` interface lets the agent run against an in-process simulator for zero-friction demos, or swap to live AWS CloudWatch/ECS/SQS APIs with a single env var change.

---

## Architecture at a Glance

```
                         ┌────────────────────────────────────┐
                         │   Streamlit Incident Dashboard     │
                         │   (Live SLA Charts + Chaos Lab)    │
                         └─────────────────┬──────────────────┘
                                           │ User Alert / Prompt
                         ┌─────────────────▼──────────────────┐
                         │    StrandsOps SRE Agent (Brain)    │
                         │    (Powered by Strands SDK)        │
                         └─────────────────┬──────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐              ┌──────────────────┐
│   OBSERVABILITY  │             │   SAFETY GATE    │              │   REMEDIATION    │
│ • inspect_telemetry            │ • analyze_blast_ │              │ • quarantine_    │
│ • fetch_error_logs             │   radius         │              │   messages       │
│ • inspect_queue_ │             │ (Dependency map  │              │ • restart_       │
│   health         │             │  risk scoring)   │              │   service        │
└────────┬─────────┘             └────────┬─────────┘              │ • rollback_      │
         │                                │                        │   config         │
         │                                │                        └────────┬─────────┘
         └────────────────────────────────┼─────────────────────────────────┘
                                          │
                         ┌────────────────▼──────────────────┐
                         │    Closed-Loop Verification       │
                         │    (verify_system_recovery)       │
                         │    Checks: Err=0%, P99 < 120ms    │
                         └────────────────┬──────────────────┘
                                          │
                         ┌────────────────▼──────────────────┐
                         │   Automated Incident Postmortem   │
                         │   (MTTD, MTTR, Root Cause, RCA)   │
                         └───────────────────────────────────┘
```

---

## How It Solves the 4 Hackathon Criteria

### 1. Idea and Impact
* **The Real Problem:** The 45-minute MTTR gap during cloud outages and on-call engineer burnout.
* **What changes for people on the other side:** Engineers sleep through the night; companies avoid \$100k+ downtime losses; customer checkouts stop failing silently.

### 2. Built on AWS
* **Strands Agents SDK (Mandatory Open Source):** Powers the core agentic reasoning loop, tool schema reflection, and multi-turn execution.
* **Amazon Bedrock (LLM Engine):** Uses Claude 3.5 Sonnet / Haiku via `boto3` for deep log correlation and root-cause analysis (funded by AWS credits).
* **AWS Architectural Semantics:** Accurately models AWS API Gateway, SQS queues with Dead-Letter Queues (DLQ), and microservice tiers.

### 3. Learning (What Broke & What We Learned)
* **The Mutating List Bug:** When quarantining SQS messages, our first implementation mutated the message list during iteration, causing the second poison pill to be skipped. Writing comprehensive unit tests caught this subtle bug immediately!
* **The "False Victory" Trap:** Early on, the agent would restart a service and immediately say "Resolved!" even while latency was still 3,000ms. We realized real SRE requires **closed-loop verification**—polling telemetry until metrics mathematically recover.
* **Agent Boundaries:** Giving an agent fewer, well-typed tools makes it 10x more reliable than giving it broad, ambiguous tools.

### 4. The Execution
* **140/140 Automated Tests Passing:** Comprehensive test suites across 6 modules cover simulator baseline invariants, all 4 chaos failure modes, SRE tools, blast-radius safety gates, the Pluggable Action Registry (all 8 plugins), semantic incident caching, live AWS adapter contracts, and mathematical soak-window verification.
* **One-Click Reproducible Demos:** One click in the UI simulates a real outage, and the agent fixes it live in under 30 seconds.

---

## Quick Start (Under 2 Minutes)

### 1. Clone & Set Up Virtualenv
```bash
cd strandops-sre
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (Strands SDK, Streamlit, Plotly, Rich, Pytest)
pip install -e ".[web,dev]"
```

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in your AWS credentials for Amazon Bedrock (or leave default for local/Ollama fallback)
```

### 3. Run the Streamlit Incident Dashboard
```bash
streamlit run src/strandops/web.py
```
*Open `http://localhost:8501` in your browser.*

### 4. Or Run the Terminal CLI
```bash
python -m strandops.cli
```

### 5. Run the Test Suite
```bash
python -m pytest tests/ -v
```

---

## The Flagship 2-Minute Demo

1. **Inject Chaos:** In the Streamlit sidebar, click **`💣 1. Inject SQS Poison Pill Storm`**.
   * *What happens:* Error rate spikes to **84.5%**, queue backlog shoots to 450 messages, and Dead-Letter Queue turns red.
2. **Prompt the Agent:** Type: *"Alert detected on SQS and inventory worker. Investigate, verify safety, remediate, and verify recovery."*
3. **Watch it Work:**
   * 🔍 **Inspects Telemetry:** Flags `inventory-worker` exceeding SLA.
   * 📜 **Reads Logs:** Catches `JSONDecodeError` on messages `msg-bad-881`, `882`, and `883`.
   * 🛡️ **Evaluates Blast Radius:** Confirms quarantining those 3 messages won't affect valid customer orders.
   * ⚡ **Remediates:** Moves poison pills to DLQ.
   * ✅ **Verifies:** Confirms error rate drops to **0.0%** and P99 latency returns to **< 50ms**.
   * 📄 **Generates Postmortem:** Switch to the **Postmortem tab** to see the complete executive report ready for engineering leadership.

---

## Project Structure

```
strandops-sre/
├── pyproject.toml               # Dependencies & build setup
├── .env.example                 # Bedrock & model provider configuration
├── README.md                    # This file
├── DEMO.md                      # Step-by-step video script
├── src/strandops/
│   ├── __init__.py
│   ├── agent.py                 # Strands SRE Coordinator Agent (Two-Tier Architecture)
│   ├── cache.py                 # Semantic Incident Cache (< 10ms repeat resolution)
│   ├── cli.py                   # Rich terminal SRE console
│   ├── web.py                   # Streamlit Incident Command Center Dashboard
│   ├── plugins/                 # Pluggable SRE Runbook Registry
│   │   ├── base.py              # RemediationPlugin abstract base class
│   │   ├── actions.py           # Typed plugins (scale, flush, trip, reroute, etc.)
│   │   └── registry.py          # ActionRegistry singleton
│   ├── simulator/
│   │   ├── models.py            # Microservice, Queue, Log, and Incident models
│   │   ├── provider.py          # Abstract CloudProvider interface (Strategy Pattern)
│   │   ├── aws_provider.py      # Live AWS Adapter (boto3 CloudWatch, ECS, SQS)
│   │   └── cloud.py             # In-process cloud simulation & Chaos Engine
│   └── tools/
│       ├── telemetry.py         # inspect_telemetry tool
│       ├── diagnostics.py       # fetch_error_logs & inspect_queue_health tools
│       ├── safety.py            # analyze_blast_radius tool
│       ├── remediation.py       # execute_remediation tool (dispatches via ActionRegistry)
│       ├── verification.py      # verify_system_recovery tool (soak-window verification)
│       └── postmortem.py        # generate_incident_postmortem tool
└── tests/                       # 140 automated tests across 6 modules (100% passing)
```

---

## Team & Acknowledgements
Built with ❤️ for **WeMakeDevs Bharat Builds 2026**. Special thanks to the AWS open-source team for the **Strands Agents SDK**!
