# StrandsOps — 3-Minute Demo Video Script

For **WeMakeDevs First Commit**: judges watch a **recorded 3-minute video** (no live call). Show **what it does**, **who it is for**, and **where AWS fits**.

---

## What to share on screen (recommended order)

| Time | Screen | Why |
|------|--------|-----|
| 0:00–0:25 | You (optional) **or** title slide + GitHub/README | Problem + who it’s for |
| 0:25–2:20 | **Streamlit** at `http://localhost:8501` | Real Strands + Bedrock agent loop (AWS load-bearing) |
| 2:20–2:40 | **Postmortem** tab in Streamlit | Proof + learning |
| 2:40–2:55 | **Vercel UI** [strandops-sre.vercel.app](https://strandops-sre.vercel.app) | Polished desk / Best UI signal (5–10s only) |
| 2:55–3:00 | GitHub repo URL | Close |

**Do not** open `.env` or show access keys on camera.

**Primary demo surface = Streamlit locally.** Vercel is the public browser simulator only (no Bedrock keys — by design).

---

## How to run locally (before you hit Record)

### 1. One-time setup

```bash
cd strandops-sre
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[web,dev]"
copy .env.example .env
```

Edit `.env` (keep this file private):

```env
MODEL_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_ACCOUNT_ID=your_12_digit_id
CLOUD_BACKEND=simulator
```

Confirm Claude access is enabled in **Amazon Bedrock** for `us-east-1`.

### 2. Start the agent desk (this is what you screen-share)

```bash
streamlit run src/strandops/web.py
```

Browser opens **http://localhost:8501**.  
Sidebar should show model access active (green) when keys work.

### 3. Optional second tab (for the last 15 seconds)

Open [https://strandops-sre.vercel.app](https://strandops-sre.vercel.app) in another browser tab — switch to it only at the end.

### 4. Pre-roll checklist

- [ ] Cluster reset / healthy (green / all clear)  
- [ ] Chat history cleared or fresh session  
- [ ] Microphone levels OK; close Discord/Slack notifications  
- [ ] Zoom browser to ~110% so charts/chat are readable  
- [ ] Practice once: poison pill → Enter → wait for tools → postmortem  

---

## Spoken script (≈ 3:00) — word-for-word friendly

### [0:00–0:25] Hook + who it’s for  
**On screen:** Face or title “StrandsOps — On-call SRE co-pilot” + GitHub.

> “Hi — I’m building **StrandsOps** for First Commit.  
> It’s for **on-call engineers** at 3 AM, when checkout is down and MTTR is usually 45 to 90 minutes of digging through logs.  
> StrandsOps investigates the outage, checks blast radius, applies a **safe typed fix**, soak-verifies recovery, then writes a postmortem.”

### [0:25–0:45] Where AWS fits  
**On screen:** Streamlit sidebar — account / region / Bedrock model.

> “AWS is load-bearing here: we use the open-source **Strands Agents SDK** for the agent and tools, and **Amazon Bedrock** with Claude for reasoning.  
> The cluster is an AWS-shaped simulator — API Gateway, SQS with DLQ, and microservices — so the demo is reproducible without risking a live production account.”

### [0:45–1:00] Inject chaos  
**On screen:** Click **Inject SQS Poison Pill Storm**. Point at red alert, error spike, queue backlog.

> “I inject an SQS poison-pill storm. Inventory workers crash on bad JSON — error rate jumps toward 84%, backlog climbs, DLQ activity shows up. Same failure pattern you’d see in a real SQS outage.”

### [1:00–2:05] Agent triage (let it run; narrate lightly)  
**On screen:** Chat auto-prompt or press Enter. Watch tool calls / reply stream. Scroll if needed so tools are visible.

> “I ask it to investigate, check blast radius, remediate, and verify.  
> Watch: it reads telemetry and logs, finds the poison message IDs, confirms quarantine is safe, moves them to the DLQ — no raw shell, only bounded primitives — then soak-checks that error rate is back within SLA — under 1% — and P99 is healthy.  
> It never declares victory on a single 200 OK.”

*(If Bedrock is slow: stay calm — “It’s calling Bedrock and tools…” — don’t skip ahead.)*

### [2:05–2:25] Postmortem  
**On screen:** **Postmortems** tab → generate/open report. Scroll RCA + SLA proof.

> “It writes an incident postmortem: root cause, MTTR, remediation steps, and follow-ups for the team. That’s the handoff a real on-call would leave for leadership.”

### [2:25–2:40] What we learned (judging criterion)  
**On screen:** Stay on postmortem or brief cut to healthy metrics.

> “What we learned building this: mutating a queue list while quarantining skipped a poison pill — tests caught it. And early versions declared ‘fixed’ while latency was still thousands of milliseconds — that’s why soak verification is mandatory.”

### [2:40–2:55] Public UI flash  
**On screen:** Switch to Vercel tab — chaos lab / service map briefly.

> “There’s also a public incident desk at strandops-sre.vercel.app for interactive demos. Bedrock keys stay on my machine only — the hosted UI is the safe simulator front-end.”

### [2:55–3:00] Close  
**On screen:** GitHub `https://github.com/Vapa1510/strandops-sre`

> “Repo is public on GitHub. StrandsOps — safer on-call with Strands and Bedrock. Thanks.”

---

## Backup if Bedrock fails during recording

1. Still inject chaos and show metrics turning red (simulator works without Bedrock).  
2. Say: “Agent needs Bedrock; here’s the same triage loop on the public desk.”  
3. Switch to Vercel → **Stage outage** → **Run triage** → show steps + postmortem.  
4. Still name **Strands Agents SDK** + **Bedrock** as the local AWS path in the voiceover.

---

## Recording tips

- One continuous take is fine; light cuts OK if you stay under 3:00.  
- Prefer **1080p**, clear mic, no music under speech.  
- Speak to the **five judging lenses**: idea/impact, Built on AWS, learning, execution, demo clarity.  
- End on a working green cluster or a completed postmortem — never on an error stack.
