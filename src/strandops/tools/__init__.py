"""Tool registry for the StrandsOps SRE Agent."""

from strandops.tools.telemetry import inspect_telemetry
from strandops.tools.diagnostics import fetch_error_logs, inspect_queue_health
from strandops.tools.safety import analyze_blast_radius
from strandops.tools.remediation import execute_remediation
from strandops.tools.verification import verify_system_recovery
from strandops.tools.postmortem import generate_incident_postmortem

SRE_TOOLS = [
    inspect_telemetry,
    fetch_error_logs,
    inspect_queue_health,
    analyze_blast_radius,
    execute_remediation,
    verify_system_recovery,
    generate_incident_postmortem,
]
