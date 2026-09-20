"""Streamlit Incident Command Center Dashboard for StrandsOps.

Run with: streamlit run src/strandops/web.py
"""
from __future__ import annotations

import os
import sys

# Add src to pythonpath
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import streamlit as st
    import plotly.express as px
except ImportError:
    print("[ERROR] streamlit and plotly required. Run: pip install streamlit plotly")
    sys.exit(1)

from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario
from strandops.agent import create_sre_agent, get_provider_info
from strandops.sla import max_error_rate_pct, max_p99_latency_ms


st.set_page_config(
    page_title="StrandsOps — Incident Desk",
    page_icon="🛡️",
    layout="wide",
)


def get_agent():
    """Cache the Strands agent instance in session state across reruns."""
    if "agent" not in st.session_state:
        st.session_state.agent = create_sre_agent()
    return st.session_state.agent


# Top Header & Status Banner
col_header, col_status = st.columns([3, 1])
with col_header:
    st.title("🛡️ StrandsOps — Incident Desk")
    st.caption("Investigate alerts, check blast radius, fix carefully, then re-check metrics")

with col_status:
    inc = cloud.active_incident
    if inc and inc.status == "OPEN":
        st.error(f"🚨 **ACTIVE ALERT: {inc.severity.value}**\n\n{inc.title}")
    else:
        st.success("🟢 **All clear**\n\nMetrics within SLA")

# Left Sidebar: AWS Cloud Services, Chaos Lab & Cluster Topology
with st.sidebar:
    st.header("☁️ Cloud Link")
    info = get_provider_info()
    st.markdown(f"**Linked Account:** `{info['account_id']}`")
    if info["has_credentials"]:
        st.success(f"🟢 **Model access: Active**\n\nModel: `{info['model_id']}`\n\nRegion: `{info['region']}`")
    else:
        st.info(f"🟡 **Model access: Ready**\n\nModel: `{info['model_id']}`\n\nRegion: `{info['region']}`")
        with st.expander("🔑 AWS Credentials"):
            st.caption("Add AWS keys here or edit `.env`:")
            key_id = st.text_input("AWS Access Key ID", value=os.getenv("AWS_ACCESS_KEY_ID", ""), type="password")
            secret = st.text_input("AWS Secret Access Key", value=os.getenv("AWS_SECRET_ACCESS_KEY", ""), type="password")
            region_val = st.text_input("AWS Region", value=info["region"])
            if st.button("Connect model access", use_container_width=True):
                if key_id and secret:
                    os.environ["AWS_ACCESS_KEY_ID"] = key_id
                    os.environ["AWS_SECRET_ACCESS_KEY"] = secret
                    os.environ["AWS_REGION"] = region_val
                    if "agent" in st.session_state:
                        del st.session_state["agent"]
                    st.success("Connected.")
                    st.rerun()

    st.divider()
    st.header("⚡ Chaos Lab")
    st.markdown("Inject a realistic outage, then watch triage and recovery:")

    if st.button("💣 1. Inject SQS Poison Pill Storm", use_container_width=True):
        cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
        st.session_state.quick_prompt = "Critical alert: SQS queue and inventory workers are failing. Investigate root cause, ensure safe blast radius, remediate, and verify recovery."
        st.rerun()

    if st.button("⚠️ 2. Inject Payment Gateway OOM", use_container_width=True):
        cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
        st.session_state.quick_prompt = "Alert: Payment Gateway latency spiked to 3200ms and memory is near limit. Triage and remediate."
        st.rerun()

    if st.button("💥 3. Inject Bad Rate-Limit Deploy", use_container_width=True):
        cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
        st.session_state.quick_prompt = "Alert: API Gateway is rejecting 85% of customer traffic with HTTP 429. Investigate and restore service."
        st.rerun()

    if st.button("🛑 4. Inject DB Pool Deadlock", use_container_width=True):
        cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)
        st.session_state.quick_prompt = "Critical alert: Order Service database connection pool is starved and requests are timing out. Triage and remediate."
        st.rerun()

    if st.button("🔄 Reset Cluster to Healthy", use_container_width=True):
        cloud.reset()
        st.success("Cluster restored to healthy baseline.")
        st.rerun()

    st.divider()
    st.header("🗺️ Service Topology Health")
    telemetry = cloud.get_telemetry()
    for t in telemetry:
        icon = "🟢" if t.status.value == "healthy" else ("🟡" if t.status.value == "degraded" else "🔴")
        st.markdown(f"**{icon} `{t.service_name}`**")
        st.caption(f"P99: {t.p99_latency_ms:.0f}ms | Err: {t.error_rate_pct:.1f}% | Mem: {t.memory_usage_mb:.0f}MB")

    queue = cloud.get_queue_state()
    q_icon = "🔴" if queue.poison_pill_ids else "🟢"
    st.markdown(f"**{q_icon} SQS: `{queue.queue_name}`**")
    st.caption(f"Visible: {queue.approximate_messages_visible} | DLQ: {queue.dead_letter_count} | Poison Pills: {len(queue.poison_pill_ids)}")

# Telemetry Overview KPI Cards
col1, col2, col3, col4 = st.columns(4)
avg_p99 = sum(t.p99_latency_ms for t in telemetry) / len(telemetry) if telemetry else 0.0
max_err = max((t.error_rate_pct for t in telemetry), default=0.0)
total_rps = sum(t.requests_per_sec for t in telemetry) if telemetry else 0.0

with col1:
    st.metric(
        "Avg P99 Latency",
        f"{avg_p99:.1f} ms",
        delta="OK" if avg_p99 <= max_p99_latency_ms() else "HIGH",
        delta_color="inverse",
    )
with col2:
    st.metric(
        "Peak Error Rate",
        f"{max_err:.1f} %",
        delta="OK" if max_err <= max_error_rate_pct() else "CRITICAL",
        delta_color="inverse",
    )
with col3:
    st.metric("Aggregate Throughput", f"{total_rps:.0f} RPS")
with col4:
    st.metric("Active Incident", inc.incident_id if inc and inc.status == "OPEN" else "None", delta="SEV1" if inc and inc.status == "OPEN" else "Stable")

# Live SLA Chart
chart_data = [
    {
        "Service": t.service_name,
        "P99 Latency (ms)": t.p99_latency_ms,
        "Error Rate (%)": t.error_rate_pct,
        "Memory (MB)": t.memory_usage_mb,
    }
    for t in telemetry
]
df = pd.DataFrame(chart_data) if pd is not None else chart_data

fig = px.bar(
    df,
    x="Service",
    y=["P99 Latency (ms)", "Error Rate (%)"],
    barmode="group",
    title=(
        f"Service telemetry vs SLA "
        f"(P99 ≤ {max_p99_latency_ms():.0f} ms · error ≤ {max_error_rate_pct()}%)"
    ),
    height=280,
)
st.plotly_chart(fig, use_container_width=True, key="telemetry_chart")

# Main Workspace Tabs
tab_chat, tab_postmortem, tab_logs = st.tabs(["On-Call Console", "Postmortems", "Log Stream"])

with tab_chat:
    st.subheader("On-call console")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi — I'm **StrandsOps**. Pick a chaos scenario in the sidebar to stage an outage, or tell me which service looks wrong.",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = None
    if "quick_prompt" in st.session_state:
        prompt = st.session_state.pop("quick_prompt")

    if user_input := st.chat_input("Describe the alert or ask for a fix..."):
        prompt = user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Checking telemetry, logs, and blast radius..."):
                triage_banner = ""
                try:
                    from strandops.agent import fast_triage_incident
                    if inc and inc.affected_services:
                        t_info = fast_triage_incident(inc.affected_services[0])
                        if not t_info.get("escalation_needed"):
                            triage_banner = "**Seen this before** — using the playbook from a prior incident.\n\n"
                        else:
                            triage_banner = "**New pattern** — running a full investigation.\n\n"

                    agent = get_agent()
                    response = agent(prompt)

                    # Extract response text
                    reply = ""
                    if hasattr(response, "message") and hasattr(response.message, "content"):
                        for block in response.message.content:
                            if hasattr(block, "text"):
                                reply += block.text
                    if not reply:
                        reply = str(response)
                    reply = triage_banner + reply
                except Exception as e:
                    err_msg = str(e)
                    err_type = type(e).__name__
                    if "NoCredentialsError" in err_type or "credentials" in err_msg.lower():
                        reply = (
                            "**Cloud credentials needed**\n\n"
                            "Investigation needs AWS credentials for model access.\n\n"
                            "**How to connect:**\n"
                            "1. Open the left sidebar and enter your **AWS Access Key ID** & **Secret Access Key**\n"
                            "2. Click **Connect model access**\n"
                            "3. Or edit `.env` in your project root with your AWS keys\n"
                            "4. Or set `MODEL_PROVIDER=ollama` in `.env` for local offline testing."
                        )
                    else:
                        reply = f"**Error ({err_type})**: {err_msg}"

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

with tab_postmortem:
    st.subheader("Incident postmortems")
    from strandops.tools.postmortem import generate_incident_postmortem
    import json as _json

    if st.button("Generate postmortem for current incident", use_container_width=True):
        pm_raw = generate_incident_postmortem()
        pm_data = _json.loads(pm_raw)
        st.session_state["last_postmortem"] = pm_data.get("markdown_report", "No postmortem available.")

    if "last_postmortem" in st.session_state:
        st.markdown(st.session_state["last_postmortem"])
    else:
        st.info("No postmortem yet. Resolve an incident first, then generate one.")

with tab_logs:
    st.subheader("Structured service logs")
    logs = cloud.get_logs(limit=25)
    log_records = [
        {
            "Timestamp": l.timestamp[11:19],
            "Level": l.level.value,
            "Service": l.service,
            "Message": l.message,
            "Error Type": l.error_type or "-",
        }
        for l in logs
    ]
    log_display = pd.DataFrame(log_records) if pd is not None else log_records
    st.dataframe(log_display, use_container_width=True)
