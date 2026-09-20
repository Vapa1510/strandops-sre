"use client";

import React from "react";
import { ServiceMetrics, QueueMetrics, SLA_MAX_P99_MS, SLA_MAX_ERROR_RATE } from "@/lib/engine";
import { Server, Database, Layers } from "lucide-react";

interface TopologyMapProps {
  services: Record<string, ServiceMetrics>;
  queue: QueueMetrics;
  onSelectService?: (serviceName: string) => void;
  selectedService?: string | null;
}

export function TopologyMap({
  services,
  queue,
  onSelectService,
  selectedService,
}: TopologyMapProps) {
  const getStatusColor = (status: ServiceMetrics["status"]) => {
    switch (status) {
      case "healthy":
        return {
          border: "border-emerald-500/35",
          bg: "bg-emerald-950/25",
          glow: "shadow-[0_0_18px_-4px_rgba(16,185,129,0.35)]",
          text: "text-emerald-400",
          badge: "bg-emerald-950 border-emerald-700 text-emerald-300",
        };
      case "degraded":
        return {
          border: "border-amber-500/50",
          bg: "bg-amber-950/30",
          glow: "shadow-[0_0_20px_-4px_rgba(245,158,11,0.4)]",
          text: "text-amber-400",
          badge: "bg-amber-950 border-amber-600 text-amber-300 animate-pulse",
        };
      case "unhealthy":
        return {
          border: "border-rose-500/70",
          bg: "bg-rose-950/40",
          glow: "shadow-[0_0_24px_-4px_rgba(244,63,94,0.45)]",
          text: "text-rose-400",
          badge: "bg-rose-950 border-rose-600 text-rose-300 animate-pulse",
        };
      case "recovering":
        return {
          border: "border-brand/50",
          bg: "bg-brand/15",
          glow: "shadow-neon-blue",
          text: "text-brand-bright",
          badge: "bg-brand/20 border-brand/40 text-brand-soft",
        };
    }
  };

  const hasDlqSurge = queue.dlq_messages > 0;

  return (
    <div id="map" className="relative w-full glass-panel p-5 sm:p-6 overflow-hidden scroll-mt-24">
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.12),transparent_65%)]" />
      </div>

      <div className="relative flex items-center justify-between mb-6 gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-brand/30 bg-brand/10">
            <Layers className="w-4 h-4 text-brand-bright" />
          </div>
          <h2 className="font-display text-base font-bold text-white tracking-tight">
            Service map
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Healthy
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Degraded
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> SLA breach
          </span>
        </div>
      </div>

      <div className="relative z-10 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-1 flex flex-col justify-center">
          {services["api-gateway"] && (
            <ServiceCard
              service={services["api-gateway"]}
              style={getStatusColor(services["api-gateway"].status)}
              isSelected={selectedService === "api-gateway"}
              onSelect={() => onSelectService?.("api-gateway")}
            />
          )}
        </div>

        <div className="md:col-span-1 flex flex-col justify-center">
          {services["order-service"] && (
            <ServiceCard
              service={services["order-service"]}
              style={getStatusColor(services["order-service"].status)}
              isSelected={selectedService === "order-service"}
              onSelect={() => onSelectService?.("order-service")}
            />
          )}
        </div>

        <div className="md:col-span-1 flex flex-col gap-4 justify-center">
          {services["payment-gateway"] && (
            <ServiceCard
              service={services["payment-gateway"]}
              style={getStatusColor(services["payment-gateway"].status)}
              isSelected={selectedService === "payment-gateway"}
              onSelect={() => onSelectService?.("payment-gateway")}
            />
          )}

          <div
            className={`rounded-2xl border p-3.5 text-xs transition-all backdrop-blur-sm ${
              hasDlqSurge
                ? "border-rose-500/60 bg-rose-950/35 shadow-[0_0_20px_-4px_rgba(244,63,94,0.4)]"
                : "border-brand/20 bg-[#071225]/75"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                <Database className="w-4 h-4 text-brand-bright" />
                <span>SQS Queue</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-brand/10 text-brand-soft border border-brand/25">
                AWS SQS
              </span>
            </div>
            <div className="space-y-1 text-slate-400 font-mono">
              <div className="flex justify-between">
                <span>In-Flight</span>
                <span className="text-slate-200">{queue.in_flight_messages}</span>
              </div>
              <div className="flex justify-between">
                <span>Approx</span>
                <span className="text-slate-200">{queue.approximate_messages}</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-white/5">
                <span className={hasDlqSurge ? "text-rose-400 font-bold" : ""}>DLQ</span>
                <span
                  className={`font-bold ${
                    hasDlqSurge ? "text-rose-400 animate-pulse" : "text-emerald-400"
                  }`}
                >
                  {queue.dlq_messages}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="md:col-span-1 flex flex-col justify-center">
          {services["inventory-worker"] && (
            <ServiceCard
              service={services["inventory-worker"]}
              style={getStatusColor(services["inventory-worker"].status)}
              isSelected={selectedService === "inventory-worker"}
              onSelect={() => onSelectService?.("inventory-worker")}
            />
          )}
        </div>
      </div>
    </div>
  );
}

interface ServiceCardProps {
  service: ServiceMetrics;
  style: {
    border: string;
    bg: string;
    glow: string;
    text: string;
    badge: string;
  };
  isSelected?: boolean;
  onSelect?: () => void;
}

function ServiceCard({ service, style, isSelected, onSelect }: ServiceCardProps) {
  return (
    <div
      onClick={onSelect}
      className={`rounded-2xl border p-4 cursor-pointer transition-all duration-200 backdrop-blur-sm ${style.border} ${style.bg} ${style.glow} ${
        isSelected ? "ring-2 ring-brand-bright scale-[1.02]" : "hover:scale-[1.01]"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-1.5">
            <Server className={`w-4 h-4 ${style.text}`} />
            <h3 className="text-sm font-bold text-slate-100">{service.name}</h3>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Port :{service.port} · {service.deployment_version}
          </div>
        </div>
        <span
          className={`px-2 py-0.5 rounded-md text-[10px] uppercase font-semibold border ${style.badge}`}
        >
          {service.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-white/5">
        <div>
          <span className="text-slate-500 block text-[10px]">P99 Latency</span>
          <span
            className={`font-semibold ${
              service.p99_ms > SLA_MAX_P99_MS
                ? "text-rose-400"
                : service.p99_ms > 80
                ? "text-amber-400"
                : "text-slate-200"
            }`}
          >
            {service.p99_ms}ms
          </span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">Error Rate</span>
          <span
            className={`font-semibold ${
              service.error_rate > 0.05
                ? "text-rose-400"
                : service.error_rate > SLA_MAX_ERROR_RATE
                ? "text-amber-400"
                : "text-slate-200"
            }`}
          >
            {(service.error_rate * 100).toFixed(1)}%
          </span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">CPU / Mem</span>
          <span className="text-slate-300">
            {service.cpu_percent}% / {service.memory_usage_mb}MB
          </span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">Pool / Replicas</span>
          <span className="text-slate-300">
            {service.connection_pool_active}/{service.connection_pool_max} · {service.replicas}x
          </span>
        </div>
      </div>
    </div>
  );
}
