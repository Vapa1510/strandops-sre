"use client";

import React from "react";
import { ServiceMetrics } from "@/lib/engine";
import { Activity, ShieldAlert, Cpu, HardDrive, Network } from "lucide-react";

interface TelemetryTableProps {
  services: Record<string, ServiceMetrics>;
}

export function TelemetryTable({ services }: TelemetryTableProps) {
  const serviceList = Object.values(services);

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h2 className="text-base font-bold text-slate-100 font-mono tracking-tight">
            Live Service Telemetry & SLA Thresholds
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          SLA Targets: P99 &lt; 200ms &bull; Error Rate &lt; 1.0%
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 text-[11px] uppercase tracking-wider">
              <th className="py-2.5 px-3">Service</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">P50 / P95 / P99</th>
              <th className="py-2.5 px-3">Error %</th>
              <th className="py-2.5 px-3">Throughput</th>
              <th className="py-2.5 px-3">CPU / Memory</th>
              <th className="py-2.5 px-3">Pool</th>
              <th className="py-2.5 px-3">Breaker</th>
              <th className="py-2.5 px-3">Replicas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {serviceList.map((svc) => {
              const isLatencyViolated = svc.p99_ms > 200;
              const isErrorViolated = svc.error_rate > 0.01;

              return (
                <tr key={svc.name} className="hover:bg-slate-900/40 transition-colors">
                  {/* Service Name & Version */}
                  <td className="py-3 px-3">
                    <div className="font-bold text-slate-100">{svc.name}</div>
                    <div className="text-[10px] text-slate-400">
                      port :{svc.port} &bull; {svc.deployment_version}
                    </div>
                  </td>

                  {/* Status */}
                  <td className="py-3 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                        svc.status === "healthy"
                          ? "bg-emerald-950/70 border-emerald-700 text-emerald-300"
                          : svc.status === "degraded"
                          ? "bg-amber-950/70 border-amber-700 text-amber-300"
                          : svc.status === "unhealthy"
                          ? "bg-rose-950/70 border-rose-700 text-rose-300 animate-pulse"
                          : "bg-cyan-950/70 border-cyan-700 text-cyan-300"
                      }`}
                    >
                      {svc.status}
                    </span>
                  </td>

                  {/* Latency */}
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

                  {/* Error Rate */}
                  <td className="py-3 px-3">
                    <span
                      className={`font-bold ${
                        isErrorViolated ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {(svc.error_rate * 100).toFixed(2)}%
                    </span>
                  </td>

                  {/* Throughput */}
                  <td className="py-3 px-3 text-slate-300">{svc.rps} rps</td>

                  {/* CPU / Memory */}
                  <td className="py-3 px-3">
                    <div className="text-slate-300">
                      <span className={svc.cpu_percent > 80 ? "text-rose-400 font-bold" : ""}>
                        {svc.cpu_percent}%
                      </span>{" "}
                      / {svc.memory_usage_mb}MB
                    </div>
                  </td>

                  {/* Connection Pool */}
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

                  {/* Circuit Breaker */}
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

                  {/* Replicas */}
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
