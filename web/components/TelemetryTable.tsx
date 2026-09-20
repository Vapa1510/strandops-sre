"use client";

import React from "react";
import { ServiceMetrics, SLA_MAX_P99_MS, SLA_MAX_ERROR_RATE } from "@/lib/engine";
import { Activity } from "lucide-react";

interface TelemetryTableProps {
  services: Record<string, ServiceMetrics>;
}

export function TelemetryTable({ services }: TelemetryTableProps) {
  const serviceList = Object.values(services);

  return (
    <div className="glass-panel p-5">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-brand/30 bg-brand/10">
            <Activity className="w-4 h-4 text-brand-bright" />
          </div>
          <h2 className="font-display text-base font-bold text-white tracking-tight">
            Live telemetry
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          SLA: P99 ≤ {SLA_MAX_P99_MS}ms · Error ≤ {(SLA_MAX_ERROR_RATE * 100).toFixed(1)}%
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-brand/10">
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-brand/15 bg-[#071225]/80 text-slate-400 text-[11px] uppercase tracking-wider">
              <th className="py-2.5 px-3 font-medium">Service</th>
              <th className="py-2.5 px-3 font-medium">Status</th>
              <th className="py-2.5 px-3 font-medium">P50 / P95 / P99</th>
              <th className="py-2.5 px-3 font-medium">Error %</th>
              <th className="py-2.5 px-3 font-medium">Throughput</th>
              <th className="py-2.5 px-3 font-medium">CPU / Memory</th>
              <th className="py-2.5 px-3 font-medium">Pool</th>
              <th className="py-2.5 px-3 font-medium">Breaker</th>
              <th className="py-2.5 px-3 font-medium">Replicas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand/10">
            {serviceList.map((svc) => {
              const isLatencyViolated = svc.p99_ms > SLA_MAX_P99_MS;
              const isErrorViolated = svc.error_rate > SLA_MAX_ERROR_RATE;

              return (
                <tr key={svc.name} className="hover:bg-brand/5 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-bold text-slate-100 font-sans">{svc.name}</div>
                    <div className="text-[10px] text-slate-500">
                      port :{svc.port} · {svc.deployment_version}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-md text-[10px] uppercase font-bold border ${
                        svc.status === "healthy"
                          ? "bg-emerald-950/70 border-emerald-700 text-emerald-300"
                          : svc.status === "degraded"
                          ? "bg-amber-950/70 border-amber-700 text-amber-300"
                          : svc.status === "unhealthy"
                          ? "bg-rose-950/70 border-rose-700 text-rose-300 animate-pulse"
                          : "bg-brand/20 border-brand/40 text-brand-soft"
                      }`}
                    >
                      {svc.status}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <div className="text-slate-300">
                      <span>{svc.p50_ms}</span> / <span>{svc.p95_ms}</span> /{" "}
                      <span
                        className={`font-bold ${
                          isLatencyViolated ? "text-rose-400" : "text-emerald-400"
                        }`}
                      >
                        {svc.p99_ms}ms
                      </span>
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`font-bold ${
                        isErrorViolated ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {(svc.error_rate * 100).toFixed(2)}%
                    </span>
                  </td>

                  <td className="py-3 px-3 text-slate-300">{svc.rps} rps</td>

                  <td className="py-3 px-3">
                    <div className="text-slate-300">
                      <span className={svc.cpu_percent > 80 ? "text-rose-400 font-bold" : ""}>
                        {svc.cpu_percent}%
                      </span>{" "}
                      / {svc.memory_usage_mb}MB
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={
                        svc.connection_pool_active >= svc.connection_pool_max
                          ? "text-rose-400 font-bold"
                          : "text-slate-300"
                      }
                    >
                      {svc.connection_pool_active}/{svc.connection_pool_max}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        svc.circuit_breaker_state === "OPEN"
                          ? "bg-rose-950 text-rose-300 border border-rose-700"
                          : "text-slate-400"
                      }`}
                    >
                      {svc.circuit_breaker_state}
                    </span>
                  </td>

                  <td className="py-3 px-3 text-slate-300">
                    {svc.replicas}/{svc.target_replicas}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
