"use client";

import React from "react";
import { ServiceMetrics, QueueMetrics } from "@/lib/engine";
import { Server, Database, Layers, Radio, AlertOctagon, CheckCircle2 } from "lucide-react";

interface TopologyMapProps {
  services: Record<string, ServiceMetrics>;
  queue: QueueMetrics;
  onSelectService?: (serviceName: string) => void;
  selectedService?: string | null;
}

export function TopologyMap({ services, queue, onSelectService, selectedService }: TopologyMapProps) {
  const getStatusColor = (status: ServiceMetrics["status"]) => {
    switch (status) {
      case "healthy":
        return {
          border: "border-emerald-500/40",
          bg: "bg-emerald-950/30",
          glow: "shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]",
          text: "text-emerald-400",
          badge: "bg-emerald-950 border-emerald-700 text-emerald-300",
          dot: "bg-emerald-400",
        };
      case "degraded":
        return {
          border: "border-amber-500/60",
          bg: "bg-amber-950/40",
          glow: "shadow-[0_0_20px_-3px_rgba(245,158,11,0.4)]",
          text: "text-amber-400",
          badge: "bg-amber-950 border-amber-600 text-amber-300 animate-pulse",
          dot: "bg-amber-400 animate-ping",
        };
      case "unhealthy":
        return {
          border: "border-rose-500/80",
          bg: "bg-rose-950/50",
          glow: "shadow-[0_0_25px_-3px_rgba(244,63,94,0.5)]",
          text: "text-rose-400",
          badge: "bg-rose-950 border-rose-600 text-rose-300 animate-bounce",
          dot: "bg-rose-500 animate-ping",
        };
      case "recovering":
        return {
          border: "border-cyan-500/60",
          bg: "bg-cyan-950/40",
          glow: "shadow-[0_0_20px_-3px_rgba(6,182,212,0.4)]",
          text: "text-cyan-400",
          badge: "bg-cyan-950 border-cyan-600 text-cyan-300",
          dot: "bg-cyan-400 animate-pulse",
        };
    }
  };

  const hasDlqSurge = queue.dlq_messages > 0;

  return (
    <div className="relative w-full rounded-xl border border-white/10 bg-slate-950/60 p-5 backdrop-blur-md overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-emerald-400" />
          <h2 className="text-base font-bold text-slate-100 font-mono tracking-tight">
            Microservice Dependency Graph & Live Mesh
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Healthy
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Degraded
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> Outage (SLA Violation)
          </span>
        </div>
      </div>

      {/* Topology Canvas Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
        {/* Tier 1: API Gateway */}
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

        {/* Tier 2: Order Service */}
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

        {/* Tier 3: Payment Gateway & SQS Queue */}
        <div className="md:col-span-1 flex flex-col gap-4 justify-center">
          {services["payment-gateway"] && (
            <ServiceCard
              service={services["payment-gateway"]}
              style={getStatusColor(services["payment-gateway"].status)}
              isSelected={selectedService === "payment-gateway"}
              onSelect={() => onSelectService?.("payment-gateway")}
            />
          )}

          {/* SQS Queue Node */}
          <div
            className={`rounded-lg border p-3.5 font-mono text-xs transition-all ${
              hasDlqSurge
                ? "border-rose-500/70 bg-rose-950/40 shadow-[0_0_20px_-3px_rgba(244,63,94,0.4)]"
                : "border-slate-800 bg-slate-900/60"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                <Database className="w-4 h-4 text-cyan-400" />
                <span>SQS Queue</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                AWS SQS
              </span>
            </div>
            <div className="space-y-1 text-slate-400">
              <div className="flex justify-between">
                <span>In-Flight:</span>
                <span className="text-slate-200">{queue.in_flight_messages} msgs</span>
              </div>
              <div className="flex justify-between">
                <span>Approx:</span>
                <span className="text-slate-200">{queue.approximate_messages} msgs</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-white/5">
                <span className={hasDlqSurge ? "text-rose-400 font-bold" : "text-slate-400"}>
                  DLQ Spike:
                </span>
                <span
                  className={`font-bold ${
                    hasDlqSurge ? "text-rose-400 animate-pulse" : "text-emerald-400"
                  }`}
                >
                  {queue.dlq_messages} msgs
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tier 4: Inventory Worker */}
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
    dot: string;
  };
  isSelected?: boolean;
  onSelect?: () => void;
}

function ServiceCard({ service, style, isSelected, onSelect }: ServiceCardProps) {
  return (
    <div
      onClick={onSelect}
      className={`rounded-xl border p-4 cursor-pointer transition-all duration-200 ${style.border} ${style.bg} ${style.glow} ${
        isSelected ? "ring-2 ring-cyan-400 scale-[1.02]" : "hover:scale-[1.01]"
      }`}
    >
      {/* Title & Status */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-1.5">
            <Server className={`w-4 h-4 ${style.text}`} />
            <h3 className="font-mono text-sm font-bold text-slate-100">{service.name}</h3>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Port :{service.port} &bull; {service.deployment_version}
          </div>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-semibold border ${style.badge}`}
        >
          {service.status}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-white/5">
        <div>
          <span className="text-slate-400 block text-[10px]">P99 Latency</span>
          <span
            className={`font-semibold ${
              service.p99_ms > 500 ? "text-rose-400" : service.p99_ms > 200 ? "text-amber-400" : "text-slate-200"
            }`}
          >
            {service.p99_ms}ms
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Error Rate</span>
          <span
            className={`font-semibold ${
              service.error_rate > 0.05
                ? "text-rose-400"
                : service.error_rate > 0.01
                ? "text-amber-400"
                : "text-slate-200"
            }`}
          >
            {(service.error_rate * 100).toFixed(1)}%
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">CPU / Mem</span>
          <span className="text-slate-300">
            {service.cpu_percent}% / {service.memory_usage_mb}MB
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Pool / Replicas</span>
          <span className="text-slate-300">
            {service.connection_pool_active}/{service.connection_pool_max} &bull; {service.replicas}x
          </span>
        </div>
      </div>
    </div>
  );
}
