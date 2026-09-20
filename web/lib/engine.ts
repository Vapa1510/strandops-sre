/**
 * In-browser cluster simulator for the StrandsOps incident dashboard.
 * Mirrors the Python cloud simulator: chaos → triage → fix → re-check SLAs.
 */

export type ServiceStatus = "healthy" | "degraded" | "unhealthy" | "recovering";
export type ClusterStatus = "NORMAL" | "INCIDENT" | "REMEDIATING";
export type ChaosScenario =
  | "poison_pill"
  | "connection_leak"
  | "circuit_breaker_trip"
  | "bad_deployment";

export interface ServiceMetrics {
  name: string;
  port: number;
  deployment_version: string;
  status: ServiceStatus;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  /** Fraction 0–1 (display as percent). */
  error_rate: number;
  rps: number;
  cpu_percent: number;
  memory_usage_mb: number;
  connection_pool_active: number;
  connection_pool_max: number;
  circuit_breaker_state: "CLOSED" | "OPEN" | "HALF_OPEN";
  replicas: number;
  target_replicas: number;
}

export interface QueueMetrics {
  queue_name: string;
  approximate_messages: number;
  in_flight_messages: number;
  dlq_messages: number;
  poison_pill_ids: string[];
}

export interface ActiveIncident {
  id: string;
  title: string;
  severity: "SEV1" | "SEV2";
  detected_at: string;
  affected_services: string[];
  actions: string[];
}

export interface ClusterState {
  status: ClusterStatus;
  services: Record<string, ServiceMetrics>;
  queue: QueueMetrics;
  active_incident: ActiveIncident | null;
  active_chaos: ChaosScenario | null;
  postmortem: string | null;
}

export interface AgentStep {
  step: "DETECT" | "DIAGNOSE" | "SAFETY_CHECK" | "REMEDIATE" | "VERIFY";
  title: string;
  details: string;
  tier: "TIER_0_CACHE" | "TIER_2_REASONING";
  timestamp: string;
}

/** SLA: match Python (P99 ≤ 120 ms, error ≤ 1%). error_rate is a fraction. */
export const SLA_MAX_P99_MS = 120;
export const SLA_MAX_ERROR_RATE = 0.01;

type InternalState = {
  chaos: ChaosScenario | null;
  incident: ActiveIncident | null;
  postmortem: string | null;
  replicas: Record<string, number>;
  versions: Record<string, string>;
  pools: Record<string, { active: number; max: number }>;
  breakers: Record<string, "CLOSED" | "OPEN" | "HALF_OPEN">;
  queue: QueueMetrics;
  draining: Set<string>;
};

function nowIso(): string {
  return new Date().toISOString();
}

function incidentId(): string {
  return `INC-${Math.random().toString(16).slice(2, 8).toUpperCase()}`;
}

function healthyBaseline(): InternalState {
  return {
    chaos: null,
    incident: null,
    postmortem: null,
    replicas: {
      "api-gateway": 2,
      "order-service": 3,
      "payment-gateway": 2,
      "inventory-worker": 2,
    },
    versions: {
      "api-gateway": "v1.8.2",
      "order-service": "v2.4.0",
      "payment-gateway": "v3.1.1",
      "inventory-worker": "v1.2.0",
    },
    pools: {
      "api-gateway": { active: 12, max: 100 },
      "order-service": { active: 18, max: 50 },
      "payment-gateway": { active: 22, max: 100 },
      "inventory-worker": { active: 4, max: 20 },
    },
    breakers: {
      "api-gateway": "CLOSED",
      "order-service": "CLOSED",
      "payment-gateway": "CLOSED",
      "inventory-worker": "CLOSED",
    },
    queue: {
      queue_name: "order-processing-queue",
      approximate_messages: 12,
      in_flight_messages: 2,
      dlq_messages: 0,
      poison_pill_ids: [],
    },
    draining: new Set(),
  };
}

let state: InternalState = healthyBaseline();

const PORTS: Record<string, number> = {
  "api-gateway": 8080,
  "order-service": 8081,
  "payment-gateway": 8082,
  "inventory-worker": 8083,
};

function buildService(
  name: string,
  overrides: Partial<ServiceMetrics> = {}
): ServiceMetrics {
  const pool = state.pools[name];
  const base: ServiceMetrics = {
    name,
    port: PORTS[name] ?? 8080,
    deployment_version: state.versions[name] ?? "v1.0.0",
    status: "healthy",
    p50_ms: 18,
    p95_ms: 38,
    p99_ms: 48,
    error_rate: 0,
    rps: state.draining.has(name) ? 0 : 145,
    cpu_percent: 14.5,
    memory_usage_mb: 220,
    connection_pool_active: pool.active,
    connection_pool_max: pool.max,
    circuit_breaker_state: state.breakers[name] ?? "CLOSED",
    replicas: state.replicas[name] ?? 2,
    target_replicas: state.replicas[name] ?? 2,
  };
  return { ...base, ...overrides };
}

function computeServices(): Record<string, ServiceMetrics> {
  const names = ["api-gateway", "order-service", "payment-gateway", "inventory-worker"];
  const out: Record<string, ServiceMetrics> = {};

  for (const name of names) {
    let svc = buildService(name);

    if (state.chaos === "poison_pill" && name === "inventory-worker") {
      svc = buildService(name, {
        status: "unhealthy",
        p99_ms: 480,
        error_rate: 0.845,
        cpu_percent: 62,
      });
    } else if (state.chaos === "circuit_breaker_trip") {
      if (name === "payment-gateway") {
        svc = buildService(name, {
          status: "unhealthy",
          p50_ms: 1200,
          p95_ms: 2800,
          p99_ms: 3450,
          error_rate: 0.42,
          memory_usage_mb: 1940,
          cpu_percent: 88,
          connection_pool_active: 98,
        });
      } else if (name === "order-service") {
        svc = buildService(name, {
          status: "degraded",
          p99_ms: 3500,
          error_rate: 0.38,
        });
      }
    } else if (state.chaos === "connection_leak" && name === "order-service") {
      svc = buildService(name, {
        status: "unhealthy",
        p99_ms: 1800,
        error_rate: 0.68,
        connection_pool_active: 50,
        cpu_percent: 71,
      });
    } else if (state.chaos === "bad_deployment" && name === "api-gateway") {
      svc = buildService(name, {
        status: "unhealthy",
        p99_ms: 62,
        error_rate: 0.892,
        cpu_percent: 44,
        deployment_version: "v1.8.3-bad",
      });
    }

    if (state.breakers[name] === "OPEN" && svc.status === "healthy") {
      svc = { ...svc, status: "degraded", circuit_breaker_state: "OPEN" };
    }

    if (state.draining.has(name)) {
      svc = { ...svc, rps: 0, status: svc.status === "healthy" ? "degraded" : svc.status };
    }

    out[name] = svc;
  }

  return out;
}

function clusterStatus(): ClusterStatus {
  if (!state.incident) return "NORMAL";
  if (state.chaos === null && state.incident) return "REMEDIATING";
  return "INCIDENT";
}

export function getClusterState(): ClusterState {
  return {
    status: clusterStatus(),
    services: computeServices(),
    queue: { ...state.queue },
    active_incident: state.incident ? { ...state.incident, actions: [...state.incident.actions] } : null,
    active_chaos: state.chaos,
    postmortem: state.postmortem,
  };
}

export function resetCluster(): ClusterState {
  state = healthyBaseline();
  return getClusterState();
}

export function injectChaos(scenario: ChaosScenario): ClusterState {
  state.postmortem = null;
  const id = incidentId();
  const detected_at = nowIso();

  // Reset baseline queue, pools, and breakers before applying new scenario
  const baseline = healthyBaseline();
  state.queue = { ...baseline.queue };
  state.pools = { ...baseline.pools };
  state.breakers = { ...baseline.breakers };
  state.versions = { ...baseline.versions };
  state.draining = new Set();

  if (scenario === "poison_pill") {
    state.chaos = scenario;
    state.queue = {
      queue_name: "order-processing-queue",
      approximate_messages: 450,
      in_flight_messages: 12,
      dlq_messages: 1248,
      poison_pill_ids: ["msg-bad-881", "msg-bad-882", "msg-bad-883"],
    };
    state.incident = {
      id,
      title: "SQS Poison Pill Storm — Inventory Worker Crashing",
      severity: "SEV1",
      detected_at,
      affected_services: ["inventory-worker", "order-processing-queue"],
      actions: [],
    };
  } else if (scenario === "circuit_breaker_trip") {
    // Maps to payment gateway memory / connection leak (Python MEMORY_LEAK_OOM)
    state.chaos = scenario;
    state.queue.dlq_messages = 0;
    state.pools["payment-gateway"] = { active: 98, max: 100 };
    state.incident = {
      id,
      title: "Payment Gateway Memory Leak & Latency Degradation",
      severity: "SEV1",
      detected_at,
      affected_services: ["payment-gateway", "order-service"],
      actions: [],
    };
  } else if (scenario === "connection_leak") {
    // Maps to DB pool starvation (Python DB_CONNECTION_STARVATION)
    state.chaos = scenario;
    state.queue.dlq_messages = 0;
    state.pools["order-service"] = { active: 50, max: 50 };
    state.incident = {
      id,
      title: "Database Connection Pool Starvation in Order Service",
      severity: "SEV2",
      detected_at,
      affected_services: ["order-service"],
      actions: [],
    };
  } else if (scenario === "bad_deployment") {
    // Maps to rate-limit misconfig (Python RATE_LIMIT_MISCONFIG)
    state.chaos = scenario;
    state.queue.dlq_messages = 0;
    state.versions["api-gateway"] = "v1.8.3-bad";
    state.incident = {
      id,
      title: "API Gateway Misconfigured Rate Limiting (v1.8.3)",
      severity: "SEV1",
      detected_at,
      affected_services: ["api-gateway"],
      actions: [],
    };
  }

  return getClusterState();
}

function markResolved(actionNote: string): void {
  if (!state.incident) return;
  state.incident.actions.push(actionNote);
  state.chaos = null;
}

function restoreHealthyPools(): void {
  state.pools = healthyBaseline().pools;
  state.versions["api-gateway"] = "v1.8.2";
  state.breakers = healthyBaseline().breakers;
}

export function executeRemediation(
  action: string,
  target: string
): { success: boolean; message: string; state: ClusterState } {
  const act = action.trim().toLowerCase().replace(/-/g, "_");
  const tgt = target.trim().toLowerCase().replace(/ /g, "-").replace(/_/g, "-");

  // Alias Next.js drawer names → simulator actions
  const aliases: Record<string, string> = {
    flush_connection_pool: "restart_service",
    isolate_poison_pill: "quarantine_messages",
    rollback_deployment: "rollback_config",
    reset_circuit_breaker: "trip_circuit_breaker",
    scale_replicas: "scale_service",
  };
  const resolved = aliases[act] ?? act;

  if (act === "purge_dlq" || resolved === "purge_dlq") {
    state.queue.dlq_messages = 0;
    state.queue.poison_pill_ids = [];
    state.queue.approximate_messages = 12;
    markResolved("Purged all poison messages from Dead-Letter Queue (DLQ)");
    return {
      success: true,
      message: "Successfully purged Dead-Letter Queue (DLQ). Message count reset to 0.",
      state: getClusterState(),
    };
  }

  if (resolved === "quarantine_messages") {
    const pills = [...state.queue.poison_pill_ids];
    if (pills.length === 0 && state.chaos !== "poison_pill") {
      return {
        success: true,
        message: "No poison pills on the queue — nothing to quarantine.",
        state: getClusterState(),
      };
    }
    state.queue.dlq_messages = 0;
    state.queue.poison_pill_ids = [];
    state.queue.approximate_messages = 12;
    state.queue.in_flight_messages = 2;
    markResolved(`Quarantined ${pills.length || 3} poison messages and cleared DLQ`);
    return {
      success: true,
      message: `Quarantined ${pills.length || 3} poison messages and purged DLQ. Worker backlog cleared.`,
      state: getClusterState(),
    };
  }


  if (resolved === "restart_service") {
    if (
      (state.chaos === "circuit_breaker_trip" && tgt === "payment-gateway") ||
      (state.chaos === "connection_leak" && tgt === "order-service") ||
      act === "flush_connection_pool"
    ) {
      restoreHealthyPools();
      markResolved(`Restarted '${tgt}' and flushed hung connections`);
      return {
        success: true,
        message: `Restarted ${tgt}. Memory and connection pools are back to baseline.`,
        state: getClusterState(),
      };
    }
    restoreHealthyPools();
    if (state.incident) state.incident.actions.push(`Restarted '${tgt}'`);
    return {
      success: true,
      message: `Restarted ${tgt}.`,
      state: getClusterState(),
    };
  }

  if (resolved === "rollback_config") {
    if (state.chaos === "bad_deployment" && (tgt === "api-gateway" || tgt.includes("api"))) {
      state.versions["api-gateway"] = "v1.8.2";
      markResolved("Rolled back api-gateway to v1.8.2; restored rate_limit_rps=500");
      return {
        success: true,
        message: "Rolled back api-gateway to v1.8.2. Rate limit restored to 500 RPS.",
        state: getClusterState(),
      };
    }
    return {
      success: true,
      message: `Config rollback applied on ${tgt}.`,
      state: getClusterState(),
    };
  }

  if (resolved === "scale_service") {
    const current = state.replicas[tgt] ?? 2;
    const next = Math.max(1, Math.min(current + 2, 10));
    state.replicas[tgt] = next;
    if (state.incident) {
      state.incident.actions.push(`Scaled '${tgt}' from ${current} to ${next}`);
    }
    return {
      success: true,
      message: `Scaled ${tgt} from ${current} → ${next} replicas.`,
      state: getClusterState(),
    };
  }

  if (resolved === "trip_circuit_breaker" || act === "reset_circuit_breaker") {
    if (act === "reset_circuit_breaker") {
      state.breakers[tgt] = "CLOSED";
      return {
        success: true,
        message: `Circuit breaker on ${tgt} reset to CLOSED.`,
        state: getClusterState(),
      };
    }
    state.breakers[tgt] = "OPEN";
    if (state.incident) {
      state.incident.actions.push(`Tripped circuit breaker on '${tgt}'`);
    }
    return {
      success: true,
      message: `Circuit breaker on ${tgt} is now OPEN (shedding load).`,
      state: getClusterState(),
    };
  }

  if (resolved === "drain_traffic") {
    state.draining.add(tgt);
    return {
      success: true,
      message: `Draining new traffic from ${tgt}. In-flight requests can finish.`,
      state: getClusterState(),
    };
  }

  if (resolved === "flush_cache") {
    if (state.incident) state.incident.actions.push(`Flushed cache on '${tgt}'`);
    return {
      success: true,
      message: `Flushed cache keys on ${tgt}.`,
      state: getClusterState(),
    };
  }

  return {
    success: false,
    message: `Unknown action '${action}'. Use a runbook step from the dispatcher.`,
    state: getClusterState(),
  };
}

function withinSla(services: Record<string, ServiceMetrics>): boolean {
  return Object.values(services).every(
    (s) => s.p99_ms <= SLA_MAX_P99_MS && s.error_rate <= SLA_MAX_ERROR_RATE
  ) && state.queue.poison_pill_ids.length === 0;
}

export function generatePostmortem(incident: ActiveIncident): string {
  const services = computeServices();
  const maxErr = Math.max(...Object.values(services).map((s) => s.error_rate * 100), 0);
  const maxP99 = Math.max(...Object.values(services).map((s) => s.p99_ms), 0);
  const healthy = withinSla(services);
  const actions =
    incident.actions.length > 0
      ? incident.actions.map((a, i) => `${i + 1}. ${a}`).join("\n")
      : "1. Manual review — no remediation recorded yet";

  return `# Incident Postmortem: ${incident.title}
**Incident ID:** \`${incident.id}\` | **Severity:** \`${incident.severity}\` | **Status:** \`${healthy ? "RESOLVED" : "OPEN"}\`

---

## 1. Executive Summary
On ${incident.detected_at.slice(0, 10)}, an alert fired for **${incident.affected_services.join(", ")}**.
On-call triage reviewed telemetry and logs, checked blast radius, applied a targeted fix, and re-checked metrics before closing.

* **Mean Time to Detect (MTTD):** Alert on SLA breach (ops monitor)
* **Mean Time to Resolve (MTTR):** Measured from detection to verified recovery
* **Customer Impact:** Contained to the affected services listed above.

---

## 2. Root Cause Analysis (RCA)
* Failure signature matched the injected scenario for this demo cluster.
* Logs and queue/connection metrics pointed to the service listed in the incident title.

---

## 3. Remediation Actions Executed
${actions}

---

## 4. Closed-Loop Verification Proof (${healthy ? "VERIFIED HEALTHY" : "DEGRADED (ACTION REQUIRED)"})
* **Peak Error Rate:** ${maxErr.toFixed(1)}% (SLA: <= 1.0%)
* **P99 Latency:** ${maxP99.toFixed(1)} ms (SLA: <= 120.0 ms)
* **Queue Backlog:** ${state.queue.approximate_messages} visible messages | DLQ: ${state.queue.dlq_messages} quarantined
* **System Health:** ${healthy ? "Metrics within SLA across the cluster" : "Warning: metrics still outside SLA — keep investigating"}

---

## 5. Preventative Action Items
| Action Item | Type | Owner | Status |
|---|---|---|---|
| Add schema validation at queue ingestion | Preventative | App Team | Planned |
| Tighten alerts on DLQ / pool saturation | Monitoring | SRE Team | In Progress |
| Capture this playbook for the next similar page | Process | On-Call | Completed |

*Report written by StrandsOps at ${nowIso()}.*
`;
}

function autoFixForChaos(): { action: string; target: string; summary: string } {
  switch (state.chaos) {
    case "poison_pill":
      return {
        action: "quarantine_messages",
        target: "order-processing-queue",
        summary: "Quarantined poison pills to the DLQ so inventory workers can process valid orders again.",
      };
    case "circuit_breaker_trip":
      return {
        action: "restart_service",
        target: "payment-gateway",
        summary: "Restarted payment-gateway to flush the leaked HTTP connection pool and drop memory.",
      };
    case "connection_leak":
      return {
        action: "restart_service",
        target: "order-service",
        summary: "Restarted order-service to clear hung DB transactions and reset the pool.",
      };
    case "bad_deployment":
      return {
        action: "rollback_config",
        target: "api-gateway",
        summary: "Rolled api-gateway back to v1.8.2 and restored the 500 RPS rate limit.",
      };
    default:
      return {
        action: "inspect",
        target: "cluster",
        summary: "No active outage — cluster already within SLA.",
      };
  }
}

export function runAutonomousTriage(query: string = ""): {
  steps: AgentStep[];
  remediationSummary: string | null;
  postmortem: string | null;
  state: ClusterState;
} {
  const ts = () => nowIso();
  const steps: AgentStep[] = [];
  const q = (query || "").toLowerCase();

  const snapshot = getClusterState();
  const breached = Object.values(snapshot.services).filter(
    (s) => s.p99_ms > SLA_MAX_P99_MS || s.error_rate > SLA_MAX_ERROR_RATE
  );

  steps.push({
    step: "DETECT",
    title: breached.length ? "SLA breach on live metrics" : "Cluster looks quiet",
    details: breached.length
      ? `${breached.map((s) => s.name).join(", ")} above SLA (P99 ≤ ${SLA_MAX_P99_MS}ms, err ≤ 1%). Query: "${query || "heal"}"`
      : `No SLA breaches right now. Query noted: "${query || "status check"}"`,
    tier: "TIER_0_CACHE",
    timestamp: ts(),
  });

  if (!state.chaos && breached.length === 0) {
    steps.push({
      step: "DIAGNOSE",
      title: "Nothing to fix",
      details: "Telemetry and queue depth are within normal ranges.",
      tier: "TIER_0_CACHE",
      timestamp: ts(),
    });
    return {
      steps,
      remediationSummary: "Cluster is healthy — no remediation needed.",
      postmortem: state.postmortem,
      state: getClusterState(),
    };
  }

  const knownPlaybook = Boolean(state.chaos);
  steps.push({
    step: "DIAGNOSE",
    title: knownPlaybook ? "Matched a known failure pattern" : "Correlating logs and metrics",
    details: state.incident
      ? `Incident ${state.incident.id}: ${state.incident.title}`
      : "Scanning error logs and queue depth for a root cause.",
    tier: knownPlaybook ? "TIER_0_CACHE" : "TIER_2_REASONING",
    timestamp: ts(),
  });

  const plan = autoFixForChaos();
  steps.push({
    step: "SAFETY_CHECK",
    title: "Blast-radius check",
    details: `Proposed ${plan.action} on ${plan.target}. Downstream dependents are within the auto-remediate limit.`,
    tier: "TIER_2_REASONING",
    timestamp: ts(),
  });

  let remediationSummary: string | null = null;
  if (plan.action !== "inspect") {
    const result = executeRemediation(plan.action, plan.target);
    remediationSummary = result.success ? plan.summary : result.message;
    steps.push({
      step: "REMEDIATE",
      title: result.success ? "Fix applied" : "Fix blocked",
      details: remediationSummary,
      tier: "TIER_2_REASONING",
      timestamp: ts(),
    });
  } else if (q.includes("scale")) {
    const result = executeRemediation("scale_service", "inventory-worker");
    remediationSummary = result.message;
    steps.push({
      step: "REMEDIATE",
      title: "Scale applied",
      details: remediationSummary,
      tier: "TIER_2_REASONING",
      timestamp: ts(),
    });
  }

  const after = getClusterState();
  const ok = withinSla(after.services);
  steps.push({
    step: "VERIFY",
    title: ok ? "Recovery confirmed" : "Still degraded",
    details: ok
      ? `Re-checked metrics: error ≤ 1% and P99 ≤ ${SLA_MAX_P99_MS} ms. Queue has no poison pills.`
      : "Metrics still outside SLA — another pass or a different fix is needed.",
    tier: "TIER_2_REASONING",
    timestamp: ts(),
  });

  if (ok && state.incident) {
    state.postmortem = generatePostmortem(state.incident);
    remediationSummary =
      remediationSummary ?? "Incident cleared and metrics re-checked within SLA.";
  }

  return {
    steps,
    remediationSummary,
    postmortem: state.postmortem,
    state: getClusterState(),
  };
}
