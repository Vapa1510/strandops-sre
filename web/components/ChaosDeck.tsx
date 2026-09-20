"use client";

import React from "react";
import { Flame, Skull, DatabaseZap, ShieldAlert, GitCommit, Play, Sparkles, RefreshCcw } from "lucide-react";

interface ChaosDeckProps {
  onInjectChaos: (scenario: "poison_pill" | "connection_leak" | "circuit_breaker_trip" | "bad_deployment") => void;
  onAutonomousHeal: () => void;
  onReset: () => void;
  loading: boolean;
  hasActiveIncident: boolean;
}

export function ChaosDeck({
  onInjectChaos,
  onAutonomousHeal,
  onReset,
  loading,
}: ChaosDeckProps) {
  const scenarios = [
    {
      id: "poison_pill" as const,
      title: "SQS Poison Pill",
      description:
        "Three bad JSON messages hit the queue. Workers crash on parse; backlog climbs to ~450, DLQ to 18.",
      icon: Skull,
      accent: "group-hover:border-rose-400/50 group-hover:shadow-[0_0_28px_-8px_rgba(244,63,94,0.45)]",
      iconColor: "text-rose-400",
      badge: "SEV-1",
    },
    {
      id: "connection_leak" as const,
      title: "DB Pool Exhaustion",
      description:
        "Order-service pool sticks at 50/50 with ~120 waiters. Checkout P99 climbs toward 1.8s.",
      icon: DatabaseZap,
      accent: "group-hover:border-amber-400/50 group-hover:shadow-[0_0_28px_-8px_rgba(245,158,11,0.4)]",
      iconColor: "text-amber-400",
      badge: "SEV-2",
    },
    {
      id: "circuit_breaker_trip" as const,
      title: "Payment Conn Leak",
      description:
        "Payment-gateway HTTP pool leaks; memory near 1940/2048 MB and P99 around 3450 ms.",
      icon: ShieldAlert,
      accent: "group-hover:border-yellow-400/50 group-hover:shadow-[0_0_28px_-8px_rgba(234,179,8,0.35)]",
      iconColor: "text-yellow-400",
      badge: "SEV-1",
    },
    {
      id: "bad_deployment" as const,
      title: "Bad Rate-Limit Deploy",
      description:
        "api-gateway v1.8.3 drops the limiter from 500 RPS to 5 RPS — most traffic gets 429s.",
      icon: GitCommit,
      accent: "group-hover:border-brand-bright/50 group-hover:shadow-neon-blue",
      iconColor: "text-brand-bright",
      badge: "SEV-1",
    },
  ];

  return (
    <div id="chaos" className="glass-panel p-5 sm:p-6 scroll-mt-24">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-rose-500/30 bg-rose-500/10">
            <Flame className="w-4 h-4 text-rose-400" />
          </div>
          <div>
            <h2 className="font-display text-lg font-bold text-white tracking-tight">
              Chaos lab
            </h2>
            <p className="text-xs text-slate-400">Stage a realistic outage, then run triage</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={onAutonomousHeal}
            disabled={loading}
            className="btn-brand !text-xs !py-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>Run triage</span>
          </button>
          <button onClick={onReset} disabled={loading} className="btn-ghost !text-xs !py-2">
            <RefreshCcw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          return (
            <div
              key={sc.id}
              className={`group flex flex-col justify-between rounded-2xl border border-brand/15 bg-[#071225]/70 p-4 transition-all duration-300 ${sc.accent}`}
            >
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${sc.iconColor}`} />
                    <span className="text-sm font-semibold text-slate-100">{sc.title}</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-rose-950/70 border border-rose-800/80 text-rose-300">
                    {sc.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{sc.description}</p>
              </div>

              <button
                onClick={() => onInjectChaos(sc.id)}
                disabled={loading}
                className="flex items-center justify-center gap-1.5 w-full py-2 px-3 rounded-xl bg-brand/10 hover:bg-brand/20 border border-brand/25 hover:border-brand/45 text-slate-100 text-xs font-medium transition-colors disabled:opacity-50"
              >
                <Play className="w-3 h-3 text-brand-bright" />
                <span>Stage outage</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
