"use client";

import React from "react";
import { Shield, Activity, Gauge, AlertTriangle, ArrowRight } from "lucide-react";
import { ClusterState, SLA_MAX_ERROR_RATE, SLA_MAX_P99_MS } from "@/lib/engine";

interface HeroStripProps {
  clusterState: ClusterState | null;
  onRunTriage: () => void;
  onScrollToChaos: () => void;
  loading: boolean;
}

export function HeroStrip({
  clusterState,
  onRunTriage,
  onScrollToChaos,
  loading,
}: HeroStripProps) {
  const services = clusterState ? Object.values(clusterState.services) : [];
  const peakError = services.length
    ? Math.max(...services.map((s) => s.error_rate * 100))
    : 0;
  const maxP99 = services.length ? Math.max(...services.map((s) => s.p99_ms)) : 0;
  const status = clusterState?.status ?? "NORMAL";
  const slaOk =
    peakError <= SLA_MAX_ERROR_RATE * 100 && maxP99 <= SLA_MAX_P99_MS && status === "NORMAL";

  return (
    <section className="cloudrix-spotlight text-center pt-6 pb-2 sm:pt-10">
      <div className="flex flex-wrap items-center justify-center gap-2 mb-5 animate-fade-up">
        <span className="glass-chip">
          <Shield className="w-3.5 h-3.5 text-brand-bright" />
          Blast-radius gated remediations
        </span>
        <span className="glass-chip">
          <Activity className="w-3.5 h-3.5 text-brand-bright" />
          Soak-verified recovery
        </span>
      </div>

      <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-white max-w-3xl mx-auto leading-[1.15] animate-fade-up">
        On-call desk for{" "}
        <span className="bg-gradient-to-r from-brand-bright to-cyan-300 bg-clip-text text-transparent">
          cloud incidents
        </span>
      </h1>

      <p className="mt-4 max-w-xl mx-auto text-sm sm:text-base text-slate-400 leading-relaxed animate-fade-up">
        Investigate alerts, check blast radius, apply a bounded fix, then re-check metrics
        before you close the ticket.
      </p>

      <div className="mt-7 flex flex-wrap items-center justify-center gap-3 animate-fade-up">
        <button
          type="button"
          onClick={onScrollToChaos}
          className="btn-ghost"
        >
          Stage an outage
        </button>
        <button
          type="button"
          onClick={onRunTriage}
          disabled={loading}
          className="btn-brand"
        >
          Run triage
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3.5 max-w-3xl mx-auto animate-fade-up">
        <StatCard
          icon={<AlertTriangle className="w-4 h-4" />}
          value={`${peakError.toFixed(1)}%`}
          label="Peak error rate"
          tone={peakError > SLA_MAX_ERROR_RATE * 100 ? "danger" : "ok"}
        />
        <StatCard
          icon={<Gauge className="w-4 h-4" />}
          value={`${maxP99.toFixed(0)} ms`}
          label="Max P99 latency"
          tone={maxP99 > SLA_MAX_P99_MS ? "danger" : "ok"}
        />
        <StatCard
          icon={<Activity className="w-4 h-4" />}
          value={status}
          label={slaOk ? "Cluster within SLA" : "Attention required"}
          tone={status === "INCIDENT" ? "danger" : status === "REMEDIATING" ? "warn" : "ok"}
        />
      </div>
    </section>
  );
}

function StatCard({
  icon,
  value,
  label,
  tone,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
  tone: "ok" | "warn" | "danger";
}) {
  const toneClass =
    tone === "danger"
      ? "text-rose-300"
      : tone === "warn"
      ? "text-amber-300"
      : "text-emerald-300";

  return (
    <div className="glass-panel-strong relative overflow-hidden px-5 py-4 text-left">
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-brand/20 to-transparent pointer-events-none animate-glow-pulse" />
      <div className="relative flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg border border-brand/30 bg-brand/10 text-brand-bright">
          {icon}
        </div>
        <div>
          <div className={`font-display text-2xl font-bold tracking-tight ${toneClass}`}>
            {value}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">{label}</div>
        </div>
      </div>
    </div>
  );
}
