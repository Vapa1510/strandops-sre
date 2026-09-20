# 🎬 StrandsOps SRE — Interactive Video Demo Script & Screen-Share Guide

> **Target Duration:** 2 minutes 45 seconds (Strictly under 3 minutes)  
> **Speaker:** Solo Builder / Team Leader (Vansh Agarwal)  
> **Local Hosting URL:** [http://localhost:3000](http://localhost:3000) (or live at [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app))  
> **GitHub Repository:** [https://github.com/Vapa1510/strandops-sre](https://github.com/Vapa1510/strandops-sre)  
> **AWS Account ID:** `3792-6468-7588` | **Region:** `us-east-1`  
> **Active Model:** **Anthropic Claude 3.5 Sonnet only** via Amazon Bedrock  
> **Track:** BUILD IT Track (Agents & AI) — WeMakeDevs Bharat Builds 2026  

---

## 🖥️ Screen Setup (Before You Hit Record)

1. **Browser Window (Chrome/Edge):**
   * **Tab 1:** `http://localhost:3000` (StrandsOps Command Center — reset to nominal state).
   * **Tab 2:** `https://github.com/Vapa1510/strandops-sre` (GitHub Repo).
2. **Display Settings:**
   * Resolution: **1080p (1920x1080)**.
   * Browser Zoom: **100%** (so all latency numbers, status pills, and AWS badges are sharp).
3. **Chat Prompts (Copy these to a scratchpad to paste quickly during recording):**
   * **Prompt 1:** `Investigate P99 latency spike and DLQ backlog on order-processing-queue`
   * **Prompt 2:** `Check blast radius before executing remediation`

---

## ⏱️ Scene-by-Scene Timed Walkthrough

```
┌──────────────┬───────────────────────────────┬───────────────────────────────┐
│ Time         │ Section                       │ Screen / Tab to Show          │
├──────────────┼───────────────────────────────┼───────────────────────────────┤
│ 0:00 – 0:35  │ 1. About the Project          │ Tab 1: Header & Topology Map  │
│ 0:35 – 1:25  │ 2. Chaos Injection & Live Chat│ Tab 1: Chaos Deck + Chat Box  │
│ 1:25 – 1:55  │ 3. 5-Step Sonnet Loop & SRE   │ Tab 1: Agent Console Stream   │
│ 1:55 – 2:20  │ 4. Postmortem & AWS Stack     │ Tab 1: Postmortem Modal       │
│ 2:20 – 2:45  │ 5. Learnings, Tests & Wrap-Up │ Tab 2: GitHub Repository      │
└──────────────┴───────────────────────────────┴───────────────────────────────┘
```

---

### ⏱️ [0:00 – 0:35] PART 1: About the Project (The 3 AM On-Call Problem)

**🖥️ Screen Action:**
* Start on **Tab 1** (`http://localhost:3000`).
* Move your mouse to the **Header Bar**:
  * Hover over **`AWS: 3792-6468-7588`**.
  * Hover over **`Region: us-east-1`**.
  * Hover over **`Bedrock Claude 3.5 Sonnet`** badge.
* Point to the healthy **Microservice Topology Map** (all green nodes).

**🎙️ What to Say:**
> *"Hi everyone, I’m Vansh. Today I’m presenting **StrandsOps SRE** — an autonomous on-call co-pilot built with the **Strands Agents SDK** and **Amazon Bedrock**, using **Anthropic Claude 3.5 Sonnet exclusively**.*
>
> *If you’ve ever been on-call, you know the dread: it’s 3 AM, PagerDuty starts blaring, and cloud downtime is costing \$5,600 every minute. The real bottleneck isn't detecting the alert — it’s the 45 to 90 minutes humans spend panicking, sifting through logs, and guessing what broke.*
>
> *StrandsOps solves this. It acts like an experienced on-call SRE that catches alarms, diagnoses root causes, evaluates blast radius, and applies verified fixes before an engineer even wakes up."*

---

### ⏱️ [0:35 – 1:25] PART 2: Live Chaos Injection & Interactive Chat

**🖥️ Screen Action:**
1. Scroll down to the **Chaos Engineering Deck**.
2. Click **"Inject Chaos"** on **"SQS Poison Pill"** (or "DB Pool Exhaustion").
3. Point your mouse to the **Topology Map**:
   * Show `inventory-worker` turning **Red (Unhealthy)**.
   * Show **DLQ Spike: 1,248 msgs**.
   * Show **P99 Latency: 3,400ms** violating SLA.
4. Scroll to the **Autonomous SRE Console** input box at the bottom.
5. **Paste and Send Prompt 1:**
   > `Investigate P99 latency spike and DLQ backlog on order-processing-queue`

**🎙️ What to Say:**
> *"Let’s see it in action. Right now, our microservices are healthy. I’ll trigger a critical SEV-1 outage: an **SQS Poison Pill** storm.*
>
> *Immediately, our dead-letter queue surges to over 1,200 messages, the worker container panics, and P99 latency spikes to 3,400 milliseconds.*
>
> *Now, instead of manually digging through CloudWatch tabs, I’ll ask our agent directly in natural language:*
> *'Investigate P99 latency spike and DLQ backlog on order-processing-queue.'*"*

---

### ⏱️ [1:25 – 1:55] PART 3: Anthropic Claude 3.5 Sonnet Reasoning & Safety Gate

**🖥️ Screen Action:**
* Focus on the **Agent Console** as the 5 reasoning steps stream in:
  1. `[1/5] DETECT` (Anomaly fingerprint matched).
  2. `[2/5] DIAGNOSE` (Anthropic Claude 3.5 Sonnet correlates CloudWatch logs and identifies malformed JSON schema).
  3. `[3/5] SAFETY_CHECK` (Blast Radius Gate: validates <=25% cluster disruption).
  4. `[4/5] REMEDIATE` (Autonomous execution: isolates bad payload & purges DLQ).
  5. `[5/5] VERIFY` (3-sample soak verification with jitter variance).
* Look up at the **Topology Map**: watch it transition from **Red $\rightarrow$ Cyan (Recovering) $\rightarrow$ Neon Green (Healthy)**!

**🎙️ What to Say:**
> *"Watch how **Anthropic Claude 3.5 Sonnet** analyzes the incident:*
> * *Step 1: **DETECT** flags the SLA breach in under 5 milliseconds.*
> * *Step 2: **DIAGNOSE** leverages Claude 3.5 Sonnet to correlate CloudWatch traces and pinpoint the malformed JSON deserialization failure.*
> * *Step 3: Crucially, our **SAFETY_CHECK** gate calculates the dependency blast radius to ensure no cascading restart knocks down our database.*
> * *Step 4: **REMEDIATE** dispatches precision AWS API primitives — quarantining the poison pill and draining the DLQ.*
> * *Step 5: **VERIFY** runs a 3-checkpoint soak test to mathematically prove latency and error rates have normalized below SLA."*

---

### ⏱️ [1:55 – 2:20] PART 4: Automated Postmortem & AWS Architecture

**🖥️ Screen Action:**
1. Click the purple button: **"View Incident Postmortem"**.
2. Scroll through the modal:
   * Point out **Incident ID**, **Severity: SEV-1**, and **Lead AI Responder: Bedrock Claude 3.5 Sonnet**.
   * Highlight the **RCA, Timeline, and Preventative Action Items**.
3. Click **"Copy Markdown"** (shows checkmark).
4. Close the modal (`Esc` or `Close`).

**🎙️ What to Say:**
> *"Once resolved, StrandsOps generates an **Executive Incident Postmortem** with complete Root Cause Analysis, timeline, and preventative action items ready to share with engineering leadership.*
>
> *Our architecture is tightly coupled with AWS:*
> * ***Strands Agents SDK** coordinates the reasoning loop and tool schema reflection.*
> * ***Amazon Bedrock with Anthropic Claude 3.5 Sonnet** performs the deep log and trace synthesis.*
> * ***Amazon CloudWatch, SQS DLQs, ECS, and IAM Roles** provide our telemetry, queue isolation, and least-privilege security boundaries."*

---

### ⏱️ [2:20 – 2:45] PART 5: Learning & Growth, Tests, and Wrap-Up

**🖥️ Screen Action:**
1. Switch to **Tab 2** (`https://github.com/Vapa1510/strandops-sre`).
2. Scroll through the **README**:
   * Highlight **193 Automated Tests Passing**.
   * Highlight the **Architecture Diagram**.
   * Highlight the **Built on AWS** section with account `3792-6468-7588`.
3. Switch back to **Tab 1** for the final closing shot.

**🎙️ What to Say:**
> *"Building this as a solo developer taught me two invaluable lessons:*
> * *First, never give an LLM raw bash access. Bounded operational primitives with blast-radius gates are mandatory for enterprise SRE safety.*
> * *Second, beware the 'False Victory' trap — an agent cannot just run a command and assume it worked; it must run multi-checkpoint soak testing to prove recovery.*
>
> *All **193 automated unit, integration, and stress tests** pass in our repository, and the Command Center is live.*
>
> *Thank you to WeMakeDevs and AWS for this incredible hackathon experience!"*

---

## 💬 Summary of Questions to Ask in Chat During the Demo

| # | Question / Prompt to Type | What It Demonstrates |
|---|---------------------------|----------------------|
| **1** | `Investigate P99 latency spike and DLQ backlog on order-processing-queue` | Triggers Claude 3.5 Sonnet root-cause analysis on CloudWatch & SQS telemetry. |
| **2** | `Check blast radius before executing remediation` | Demonstrates the safety guardrail analyzing the dependency graph. |
| **3** | `Verify cluster recovery against SLA (P99 < 200ms, Error Rate < 1.0%)` | Triggers the 3-sample soak verification proof. |
