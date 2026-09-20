# StrandsOps

**On-call SRE co-pilot for cloud microservice incidents**

Built with the [Strands Agents SDK](https://strandsagents.com) and Amazon Bedrock for **WeMakeDevs Bharat Builds / First Commit 2026** (Build It — Agents & AI).

| Resource | URL |
|----------|-----|
| **Live demo (primary)** | [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app) |
| **Vercel production alias** | [https://web-ecru-nu-c1ca1gvzwd.vercel.app](https://web-ecru-nu-c1ca1gvzwd.vercel.app) |
| **Direct deployment** | [https://web-47u0x0760-vansh-agarwals-projects-8327d86e.vercel.app](https://web-47u0x0760-vansh-agarwals-projects-8327d86e.vercel.app) |
| **Source** | [github.com/Vapa1510/strandops-sre](https://github.com/Vapa1510/strandops-sre) |

The Vercel deployment is the **Next.js incident desk** (in-browser cluster simulator + triage loop). The **Python agent** (Streamlit / CLI + Bedrock) is the full Strands-powered path for local demos and judging walkthroughs.

---

## 1. Problem

### 1.1 What breaks at 3 AM

Alerting is fast. Resolution is not.

When checkout fails, an on-call engineer juggles CloudWatch, logs, SQS depth, and deployment history while half-asleep. The expensive part is not “something is wrong” — it is:

1. **Finding the root cause** among correlated symptoms  
2. **Choosing a safe action** without cascading failure  
3. **Knowing when it is actually fixed** (not just “restart returned 200”)

Industry MTTR for cloud incidents often lands in the **45–90 minute** range. Most of that time is human investigation under stress, not waiting for infrastructure.

### 1.2 What typical “AI ops” demos get wrong

| Approach | Failure mode |
|----------|----------------|
| Chatbot that summarizes logs | Advice only; no bounded action |
| LLM with raw shell / `os.system` | Unbounded blast radius; unsafe for production narratives |
| One-shot “fix” scripts | Declares victory before metrics stabilize |
| Generic RAG over runbooks | No topology, no SLA proof, no soak window |

### 1.3 Design question

> Can we build an on-call helper that investigates like a careful junior SRE: observe → diagnose → check blast radius → apply a **typed** remediation → **soak-verify** recovery → write a postmortem — with AWS (Strands + Bedrock) doing real work in the loop?

That is StrandsOps.

---

## 2. Solution approach

### 2.1 Closed-loop incident lifecycle

```
DETECT → DIAGNOSE → SAFETY (blast radius) → REMEDIATE → VERIFY (soak) → POSTMORTEM
```

Every mutating step is gated. Recovery is not claimed until live metrics stay within SLA across a soak window.

### 2.2 Problem → mechanism mapping

| Pain | Mechanism in StrandsOps |
|------|-------------------------|
| Guessing root cause from noise | Typed tools: `inspect_telemetry`, `fetch_error_logs`, `inspect_queue_health` |
| Dangerous blind restarts | `analyze_blast_radius` before remediation; auto-remediate only under a dependency limit |
| Hallucinated shell commands | Bounded primitives only (`quarantine_messages`, `restart_service`, `rollback_config`, `scale_service`, `drain_traffic`, …) |
| False “resolved” | `verify_system_recovery` with multi-checkpoint soak, memory slope, latency jitter, poison-pill checks |
| No institutional memory | Playbook cache fingerprints known failure signatures for fast repeat resolution |
| Leadership needs a write-up | `generate_incident_postmortem` with RCA, MTTR, SLA proof, follow-ups |

### 2.3 Dual surfaces (same product story)

| Surface | Role |
|---------|------|
| **Next.js (`web/`)** — Vercel | Interactive chaos lab + topology + triage UI for judges/demo visitors; in-browser engine mirrors Python scenarios |
| **Python agent** — Streamlit / CLI | Strands Agents SDK + Bedrock (or Ollama/OpenAI); full tool loop against the cloud simulator |

---

## 3. Architecture

### 3.1 High-level

```
┌─────────────────────────────────────────────────────────────────┐
│  UI: Streamlit / Rich CLI          │  UI: Next.js (Vercel)      │
│  (Strands agent + Bedrock)         │  (web/lib/engine.ts)       │
└─────────────────┬──────────────────┴─────────────┬──────────────┘
                  │                                │
                  ▼                                ▼
        ┌──────────────────┐            ┌─────────────────────┐
        │ create_sre_agent │            │ runAutonomousTriage │
        │ + SRE_TOOLS      │            │ + executeRemediation│
        └────────┬─────────┘            └──────────┬──────────┘
                 │                                 │
                 ▼                                 ▼
        ┌──────────────────┐            ┌─────────────────────┐
        │ CloudInfrastructure│          │ ClusterState        │
        │ (Python simulator) │          │ (TS simulator)      │
        └──────────────────┘            └─────────────────────┘
                 │
                 │  (provider contract exists for live AWS)
                 ▼
        CloudProvider ABC → simulator | aws_provider (partial)
```

### 3.2 Agent tools (Python)

| Tool | Responsibility |
|------|----------------|
| `inspect_telemetry` | P50/P95/P99, error %, RPS, memory; SLA breach flags |
| `fetch_error_logs` | WARN / ERROR / FATAL only |
| `inspect_queue_health` | SQS depth, DLQ, poison pill IDs |
| `analyze_blast_radius` | Dependency risk before mutate |
| `execute_remediation` | Dispatches via ActionRegistry / plugins |
| `verify_system_recovery` | Soak checkpoints + stability math |
| `generate_incident_postmortem` | Markdown RCA + SLA proof |

### 3.3 Shared SLA contract

Thresholds are centralized in `src/strandops/sla.py` (env-backed) and mirrored in the Next engine:

- **Error rate** ≤ `SLA_MAX_ERROR_RATE_PERCENT` (default **1.0%**)
- **P99 latency** ≤ `SLA_MAX_P99_LATENCY_MS` (default **120 ms**)
- Queue must have **no remaining poison pills** for healthy verification

### 3.4 Soak verification math

`verify_system_recovery` does not stop at a single green snapshot:

1. **Per-checkpoint SLA** — each service within error / P99 bounds  
2. **Memory slope** — final memory must stay within **+15%** of first checkpoint  
3. **Latency jitter** — P99 must not rise more than **+20%** across the window  
4. **Flapping** — mixed pass/fail or slope/jitter failure caps confidence and fails the soak  
5. **Confidence** — `passed_checkpoints / num_checks` (capped when unstable)

### 3.5 Chaos scenarios (aligned across Python and Next)

| Scenario | Primary failure | Typical fix |
|----------|-----------------|-------------|
| SQS poison pill | Inventory workers crash on bad JSON; backlog ~450, DLQ 18 | Quarantine messages to DLQ |
| Payment memory / conn leak | Payment gateway P99 ~3450 ms, pool exhaustion | Restart payment-gateway |
| DB pool starvation | Order-service pool 50/50 | Restart order-service |
| Bad rate-limit deploy | API gateway 429 storm (5 RPS vs 500) | Rollback config |

---

## 4. Where AWS fits

Judges look for AWS that is **load-bearing**, not decorative.

| Layer | AWS technology | Role in StrandsOps |
|-------|----------------|--------------------|
| Agent runtime | **Strands Agents SDK** | Tool schemas, multi-turn execution, system prompt |
| Reasoning | **Amazon Bedrock** (Claude 3.5 Sonnet / Haiku) | Log correlation, remediation planning |
| Auth | **IAM** access keys / roles | Bedrock invoke from local/dev |
| Domain model | **API Gateway, SQS + DLQ, ECS-style services** | Faithful AWS incident semantics in the simulator |
| Extension path | `get_cloud_provider()` + `cloud_backend` proxy | Tools honor `CLOUD_BACKEND=simulator\|aws` |

Default demo backend is the **in-process simulator** (`CLOUD_BACKEND=simulator`) so the full agent loop is reproducible without provisioning a production cluster. Bedrock still runs against your real AWS account when credentials are set.

---

## 5. Tech stack

**Python (agent path)**  
Python ≥ 3.10 · Strands Agents · boto3 · Pydantic · Rich · python-dotenv · Streamlit / Plotly / pandas · pytest

**Web (Vercel path)**  
Next.js 14 · React 18 · TypeScript · Tailwind CSS · Lucide

**Models**  
Bedrock (default) · optional OpenAI / Anthropic direct / Ollama offline

---

## 6. Repository layout

```
strandops-sre/
├── pyproject.toml
├── .env.example
├── DEMO.md                      # Video walkthrough script
├── web/                         # Next.js desk (deployed on Vercel)
│   ├── app/                     # Pages + API routes
│   ├── components/              # Hero, chaos, map, console, telemetry
│   └── lib/engine.ts            # In-browser simulator + triage
├── src/strandops/
│   ├── agent.py                 # System prompt, Bedrock wiring, create_sre_agent()
│   ├── sla.py                   # Shared SLA helpers
│   ├── cache.py                 # Playbook fingerprint cache
│   ├── cli.py                   # Terminal REPL
│   ├── web.py                   # Streamlit incident desk
│   ├── plugins/                 # Typed remediation plugins + registry
│   ├── simulator/
│   │   ├── cloud.py             # Chaos engine + metrics
│   │   ├── models.py
│   │   ├── provider.py          # CloudProvider ABC
│   │   └── aws_provider.py      # Live AWS adapter (partial)
│   └── tools/                   # Strands @tool primitives
└── tests/                       # ~193 automated tests
```

---

## 7. Quick start

### 7.1 Python agent (Streamlit / CLI)

```bash
git clone https://github.com/Vapa1510/strandops-sre.git
cd strandops-sre

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[web,dev]"
cp .env.example .env
```

Configure `.env` for Bedrock:

```env
MODEL_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20240620-v1:0
CLOUD_BACKEND=simulator
```

Enable Claude model access in the Bedrock console for that region, then:

```bash
streamlit run src/strandops/web.py    # http://localhost:8501
# or
python -m strandops.cli
# or
strandops
```

Offline alternative: set `MODEL_PROVIDER=ollama` and run a local model.

### 7.2 Next.js desk (local)

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). No AWS keys required for this surface.

### 7.3 Live web demo

- Primary: [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app)

### 7.4 Tests

```bash
python -m pytest tests/ -v
```

---

## 8. Flagship demo (≤ 2 minutes)

Scripted detail: see [`DEMO.md`](DEMO.md).

1. **Stage outage** — SQS poison pill (Streamlit sidebar or Vercel chaos lab).  
2. **Observe** — inventory-worker error ~84.5%, backlog ~450, DLQ activity.  
3. **Run triage** — agent/tools inspect telemetry & logs, check blast radius, quarantine pills.  
4. **Verify** — error ≤ 1%, P99 healthy, no poison pills.  
5. **Postmortem** — open the generated Markdown (RCA, MTTR, SLA proof, follow-ups).

---

## 9. Safety & guardrails

- Remediations are **enumerated**; no arbitrary code execution.  
- **Blast-radius** evaluation before mutate; `AUTO_REMEDIATE_BLAST_LIMIT` (default 2) bounds auto-approve.  
- **Scale** deltas clamped via `MAX_SCALE_DELTA`.  
- Verification refuses to close incidents that still flap or leak memory.  
- Secrets stay in `.env` (never commit real keys).

---

## 10. Hackathon criteria alignment

| Criterion | How StrandsOps addresses it |
|-----------|-----------------------------|
| **Idea & impact** | Shrinks MTTR for realistic AWS-shaped outages with a safe agent loop |
| **Built on AWS** | Strands SDK + Bedrock + IAM; domain model of API Gateway / SQS / DLQ / service fleets |
| **Learning** | Documented failure modes (mutating quarantine list; false victory without soak; tool-boundary discipline) |
| **Execution** | Working end-to-end demos (Vercel + local Streamlit), ~193 tests, reproducible chaos → heal path |

---

## 11. Known limitations (honest scope)

- **Chaos lab** requires `CLOUD_BACKEND=simulator` (default). With `CLOUD_BACKEND=aws`, tools route through `LiveAWSProvider` (CloudWatch / ECS / SQS), but scenario injection is not available.
- The **Vercel / Next.js** desk is an in-browser simulator for demos; the full **Strands + Bedrock** loop runs via Streamlit / CLI locally.
- Set `AWS_ACCOUNT_ID` (Python) and `NEXT_PUBLIC_AWS_ACCOUNT_ID` (web) so UI badges match your account instead of the demo default.

---

## 12. License & acknowledgements

MIT. Built for **WeMakeDevs Bharat Builds / First Commit 2026**. Thanks to the AWS open-source team for the **Strands Agents SDK** and to Amazon Bedrock for the model layer.
