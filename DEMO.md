# 🎬 StrandsOps — 2-Minute Video & Live Demo Walkthrough

This script provides the exact sequence to demonstrate **StrandsOps** for your hackathon submission video.

---

## Pre-Flight Setup

1. **Launch the Dashboard:**
   ```bash
   cd strandops-sre
   streamlit run src/strandops/web.py
   ```
   *Dashboard opens at `http://localhost:8501`.*

2. **Verify Baseline State:**
   - Notice the green indicator: `🟢 ALL SYSTEMS OPERATIONAL`.
   - Latency chart shows healthy sub-50ms bars across all 4 services.
   - SQS Queue shows healthy visible message depth.

---

## Scenario A: The SQS Poison-Pill Outage (60 Seconds)

### Step 1: The Outage (Chaos Injection)
* In the left sidebar, click the red button: **`💣 1. Inject SQS Poison Pill Storm`**.
* **What happens on screen:**
  - Status banner turns **RED**: `🚨 ACTIVE ALERT: SEV1 — SQS Poison Pill Storm`.
  - Error rate on `inventory-worker` immediately spikes to **84.5%**.
  - Visible queue backlog jumps to **450 messages**.
  - Dead-letter queue counter turns red.

### Step 2: The Agent Takes Over
* The chat box auto-populates (or type):
  > *"Critical alert: SQS queue and inventory workers are failing. Investigate root cause, ensure safe blast radius, remediate, and verify recovery."*
* Hit **Enter**.

### Step 3: Watch Autonomous Reasoning in Real Time
The agent executes the full SRE lifecycle:
1. **🔍 Telemetry Inspection:**
   `inspect_telemetry` reports `inventory-worker` error rate at 84.5% and P99 latency at 480ms.
2. **📜 Log Diagnostics:**
   `fetch_error_logs` scans recent stack traces and isolates `json.decoder.JSONDecodeError` on messages `msg-bad-881`, `msg-bad-882`, and `msg-bad-883`.
3. **📦 Queue Inspection:**
   `inspect_queue_health` confirms these 3 IDs are poison pills blocking worker execution.
4. **🛡️ Blast Radius Analysis:**
   `analyze_blast_radius` confirms quarantining these 3 messages is **SAFE** and will not drop valid consumer orders.
5. **⚡ Targeted Remediation:**
   `execute_remediation` moves the 3 poison pills to the Dead-Letter Queue.
6. **✅ Closed-Loop Verification:**
   `verify_system_recovery` double-checks telemetry: Error rate drops back to **0.0%**, P99 latency returns to **< 50ms**, and queue backlog drains.
7. **📄 Postmortem Generation:**
   `generate_incident_postmortem` generates an executive postmortem report.

### Step 4: Show the Postmortem Tab
* Click on the **"📄 Incident Postmortems"** tab in the dashboard.
* Show the automatically generated postmortem with:
  - Incident ID & SEV1 rating
  - MTTD (< 15s) and MTTR (~45s)
  - Root Cause Analysis & Quarantined Message IDs
  - Preventative action items table.

---

## Scenario B: Payment Gateway Memory Leak (30 Seconds)

1. Click **`⚠️ 2. Inject Payment Gateway OOM`**.
2. Show the latency chart: Payment Gateway latency spikes from **45ms to 3,450ms**, and memory reaches 1,940MB (near 2GB threshold).
3. Type:
   > *"Payment Gateway latency is degrading customer checkout. Triage and heal."*
4. Agent isolates connection pool leak, checks blast radius, restarts the container, and verifies latency drops back to 48ms.

---

## Key Talking Points for Your Video Voiceover

1. *"Modern cloud downtime costs over \$5,000 per minute. While alerting takes seconds, MTTR takes 45 minutes of human engineers manually digging through logs at 3 AM."*
2. *"We built StrandsOps using the open-source AWS Strands Agents SDK to eliminate the MTTR gap."*
3. *"Notice that StrandsOps doesn't guess or run dangerous raw shell commands. It uses bounded, typed remediation primitives and enforces a mandatory blast-radius check before touching any infrastructure."*
4. *"Most importantly, StrandsOps never declares victory blindly. It performs mathematical closed-loop verification, confirming error rates have dropped to 0% before writing the executive postmortem."*
