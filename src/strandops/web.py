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


st.set_page_config(
    page_title="StrandsOps — Autonomous SRE Command Center",
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
    st.title("🛡️ StrandsOps — Incident Command Center")
    st.caption("Autonomous Cloud SRE & Self-Healing Agent powered by **Strands Agents SDK** & **Amazon Bedrock** (AWS)")

with col_status:
    inc = cloud.active_incident
    if inc and inc.status == "OPEN":
        st.error(f"🚨 **ACTIVE ALERT: {inc.severity.value}**\n\n{inc.title}")
    else:
        st.success("🟢 **ALL SYSTEMS OPERATIONAL**\n\nOperating within green SLA parameters")

# Left Sidebar: AWS Cloud Services, Chaos Lab & Cluster Topology
with st.sidebar:
    st.header("☁️ AWS Cloud Services")
    info = get_provider_info()
    if info["has_credentials"]:
        st.success(f"🟢 **Amazon Bedrock: Active**\n\nModel: `{info['model_id']}`\n\nRegion: `{info['region']}`")
    else:
        st.info(f"🟡 **Amazon Bedrock: Ready**\n\nModel: `{info['model_id']}`\n\nRegion: `{info['region']}`")
        with st.expander("🔑 AWS Credentials"):
            st.caption("Add AWS keys here or edit `.env`:")
            key_id = st.text_input("AWS Access Key ID", value=os.getenv("AWS_ACCESS_KEY_ID", ""), type="password")
            secret = st.text_input("AWS Secret Access Key", value=os.getenv("AWS_SECRET_ACCESS_KEY", ""), type="password")
            region_val = st.text_input("AWS Region", value=info["region"])
            if st.button("Connect to Live Bedrock", use_container_width=True):
                if key_id and secret:
                    os.environ["AWS_ACCESS_KEY_ID"] = key_id
                    os.environ["AWS_SECRET_ACCESS_KEY"] = secret
                    os.environ["AWS_REGION"] = region_val
                    if "agent" in st.session_state:
                        del st.session_state["agent"]
                    st.success("Connected to Amazon Bedrock!")
                    st.rerun()

    st.divider()
    st.header("⚡ Chaos Engineering Lab")
    st.markdown("Inject realistic production incidents to watch the agent triage & heal:")

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
avg_p99 = sum(t.p99_latency_ms for t in telemetry) / len(telemetry)
max_err = max(t.error_rate_pct for t in telemetry)
total_rps = sum(t.requests_per_sec for t in telemetry)

with col1:
    st.metric("Avg P99 Latency", f"{avg_p99:.1f} ms", delta="-Normal" if avg_p99 < 120 else "+HIGH", delta_color="inverse")
with col2:
    st.metric("Peak Error Rate", f"{max_err:.1f} %", delta="-Healthy" if max_err <= 1.0 else "+CRITICAL", delta_color="inverse")
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
    title="Service Telemetry vs SLA Thresholds (Latency SLA: 120ms | Error Rate SLA: 1.0%)",
    height=280,
)
st.plotly_chart(fig, use_container_width=True)

# Main Workspace Tabs
tab_chat, tab_postmortem, tab_logs = st.tabs(["🤖 Autonomous SRE Console", "📄 Incident Postmortems", "📜 Live Log Stream"])

with tab_chat:
    st.subheader("Interactive Incident Command Console")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 I am **StrandsOps**, your autonomous cloud SRE agent. Click a chaos scenario in the sidebar to simulate an outage, or instruct me to investigate any degraded services.",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = None
    if "quick_prompt" in st.session_state:
        prompt = st.session_state.pop("quick_prompt")

    if user_input := st.chat_input("Command the SRE agent (e.g. 'Investigate the error spike and heal the cluster')..."):
        prompt = user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("StrandsOps analyzing telemetry, correlating error logs & checking blast radius..."):
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

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

with tab_postmortem:
    st.subheader("Automated Incident Postmortem Reports")
    from strandops.tools.postmortem import generate_incident_postmortem
    pm_raw = generate_incident_postmortem()
    import json
    pm_data = json.loads(pm_raw)
    st.markdown(pm_data.get("markdown_report", "No postmortem available."))

with tab_logs:
    st.subheader("Raw CloudWatch / Microservice Structured Logs")
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
