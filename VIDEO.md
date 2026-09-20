# 🎬 StrandsOps SRE — 3-Minute Video Demo Script

> **Target Duration:** 2 minutes 45 seconds (Strictly under 3 minutes)  
> **Speaker:** Solo Builder / Team Leader (Vansh Agarwal)  
> **Live App URL:** [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app)  
> **GitHub Repo:** [https://github.com/Vapa1510/strandops-sre](https://github.com/Vapa1510/strandops-sre)  
> **AWS Account ID:** `3792-6468-7588` (Region: `us-east-1`)  
> **Track:** BUILD IT Track (Agents & AI) — WeMakeDevs Bharat Builds 2026  

---

## 🛠️ Pre-Recording Checklist
1. Open Browser Tab 1: [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app) (Reset to nominal state if needed).
2. Open Browser Tab 2: [https://github.com/Vapa1510/strandops-sre](https://github.com/Vapa1510/strandops-sre).
3. Set browser zoom to 100% and screen resolution to 1080p (1920x1080).
4. Have a stopwatch or phone timer visible on your desk.

---

## ⏱️ Scene-by-Scene Timed Script

### **[0:00 – 0:40] Scene 1: The Problem & What StrandsOps Is**

* **🖥️ Screen Action:**
  * Start on the **StrandsOps Command Center** (`https://strandops-sre.vercel.app`).
  * Hover over the Header banner: highlight **AWS Account: `3792-6468-7588`**, **Region: `us-east-1`**, and **Bedrock Claude 3.5 Sonnet**.
  * Hover briefly across the healthy **Microservice Topology Map**.

* **🎙️ Spoken Script:**
  > *"Hi everyone, I’m Vansh, and this is **StrandsOps SRE** — an autonomous, self-healing cloud co-pilot built with the **Strands Agents SDK** and **Amazon Bedrock** for the Bharat Builds 2026 hackathon.*
  >
  > *If you’ve ever been on-call, you know the feeling: it’s 3 AM, PagerDuty is blaring, and cloud downtime is costing \$5,600 every single minute. The biggest bottleneck isn’t detection — it’s the 45 to 90 minutes humans spend sifting through logs, guessing what broke, and being terrified of running the wrong command.*
  >
  > *StrandsOps solves this. It acts like an experienced on-call SRE that investigates alarms, diagnoses root causes, checks safety blast radius, and mathematically verifies system recovery before your phone even rings."*

---

### **[0:40 – 1:40] Scene 2: Live Chaos Outage & Autonomous Bedrock Healing**

* **🖥️ Screen Action:**
  1. Scroll to the **Chaos Engineering Deck**. Click **"Inject Chaos"** on **"SQS Poison Pill"**.
  2. Point your cursor to the **Topology Map**: show `inventory-worker` turning red, DLQ spiking to 1,200+ messages, and P99 latency spiking into thousands of milliseconds.
  3. Click the green button: **"Autonomous Heal (Bedrock Agent)"**.
  4. Scroll through the **Autonomous SRE Console** as the 5 reasoning steps light up:
     - `[1/5] DETECT` (Tier-0 Cache)
     - `[2/5] DIAGNOSE` (Amazon Bedrock)
     - `[3/5] SAFETY_CHECK` (Blast Radius Gate)
     - `[4/5] REMEDIATE` (Autonomous Execution)
     - `[5/5] VERIFY` (3-Sample Soak Test)
  5. Show the topology map turn back to **Healthy Green**!

* **🎙️ Spoken Script:**
  > *"Let’s see it live in action.*
  >
  > *Right now, our cluster is healthy. I’ll inject a SEV-1 outage: an **SQS Poison Pill**. Immediately, our order-processing DLQ surges to over 1,200 messages, the worker crashes, and P99 latency violates our SLA.*
  >
  > *Now, I’ll trigger our **Autonomous Bedrock Agent**.*
  >
  > *Watch the 5-step reasoning loop:*
  > * *First, **DETECT** catches the anomaly in under 5 milliseconds using our Tier-0 semantic cache.*
  > * *Second, **DIAGNOSE** invokes Amazon Bedrock Claude 3.5 Sonnet to correlate CloudWatch traces and isolate the malformed JSON schema.*
  > * *Third, our **SAFETY_CHECK** gate calculates the dependency blast radius to ensure our remediation won't disrupt more than 25% of the cluster.*
  > * *Fourth, **REMEDIATE** dispatches precision AWS API primitives — quarantining the poison pill and purging the DLQ.*
  > * *And fifth, **VERIFY** performs a 3-checkpoint soak test to mathematically prove latency has dropped below 100 milliseconds."*

---

### **[1:40 – 2:15] Scene 3: Automated Postmortem & AWS Architecture**

* **🖥️ Screen Action:**
  1. Click **"View Incident Postmortem"** to open the modal.
  2. Scroll through: point out the **Executive Summary, Root Cause Analysis (RCA), Timeline, and Action Items**.
  3. Click **"Copy Markdown"** to show instant export. Close the modal.
  4. Switch to the **GitHub Tab** (`https://github.com/Vapa1510/strandops-sre`).

* **🎙️ Spoken Script:**
  > *"Once resolved, StrandsOps automatically generates an **Executive Incident Postmortem** with full Root Cause Analysis, timeline, and preventative action items ready for the team.*
  >
  > *Under the hood, this is deeply integrated with AWS:*
  > * ***Strands Agents SDK** powers the agentic reasoning engine and tool schemas.*
  > * ***Amazon Bedrock (Claude 3.5 Sonnet & Haiku)** drives our Two-Tier triage — Haiku for fast classification and Sonnet for complex root-cause synthesis.*
  > * ***Amazon CloudWatch, SQS DLQs, ECS, and IAM execution roles** provide our observability, messaging, and least-privilege security boundaries."*

---

### **[2:15 – 2:45] Scene 4: Learnings & Wrap-Up**

* **🖥️ Screen Action:**
  * Scroll down the **GitHub README**: show the **193 passing automated tests**, the architecture diagram, and the **Built on AWS** section.
  * Switch back to the **Vercel app** (`strandops-sre.vercel.app`) for the closing view.

* **🎙️ Spoken Script:**
  > *"Building this as a solo developer taught me critical lessons:*
  > * *First, never give an AI agent raw terminal access. Bounded operational primitives with blast-radius guardrails are essential for production safety.*
  > * *Second, we learned to avoid the 'False Victory' trap — an agent can’t just run a command and assume it worked; it must run multi-checkpoint soak testing to verify actual recovery.*
  >
  > *All 193 automated unit, integration, and stress tests are passing in the repo, and the entire app is deployed live on Vercel at `strandops-sre.vercel.app`.*
  >
  > *Thank you to WeMakeDevs and AWS for this incredible hackathon!"*

---

## 🎯 Recording Summary
* **Total Words:** ~395 words
* **Target Speed:** 135 words per minute
* **Total Time:** ~2 minutes 45 seconds
