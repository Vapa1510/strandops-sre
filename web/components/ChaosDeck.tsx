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
  hasActiveIncident,
}: ChaosDeckProps) {
  const scenarios = [
    {
      id: "poison_pill" as const,
      title: "SQS Poison Pill",
      description: "Injects malformed JSON payload into SQS queue. Worker panics, DLQ surges to 1,200+ msgs.",
      icon: Skull,
      color: "hover:border-rose-500 hover:bg-rose-950/20 text-rose-400",
      badge: "SEV-1",
    },
    {
      id: "connection_leak" as const,
      title: "DB Pool Exhaustion",
      description: "Leaks unclosed DB connections in checkout loop until pool reaches 100/100 threshold.",
      icon: DatabaseZap,
      color: "hover:border-amber-500 hover:bg-amber-950/20 text-amber-400",
      badge: "SEV-1",
    },
    {
      id: "circuit_breaker_trip" as const,
      title: "Payment Breaker Trip",
      description: "Simulates 8s payment upstream timeout, tripping order-service circuit breaker to OPEN.",
      icon: ShieldAlert,
      color: "hover:border-yellow-500 hover:bg-yellow-950/20 text-yellow-400",
      badge: "SEV-1",
    },
    {
      id: "bad_deployment" as const,
      title: "Bad Canary Deploy",
      description: "Rolls out buggy v2.5.0 release on api-gateway with native memory leak & 98% CPU load.",
      icon: GitCommit,
      color: "hover:border-purple-500 hover:bg-purple-950/20 text-purple-400",
      badge: "SEV-1",
    },
  ];

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-5 backdrop-blur-md">
      {/* Header & Primary Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2">
          <Flame className="w-5 h-5 text-rose-500 animate-pulse" />
          <h2 className="text-base font-bold text-slate-100 font-mono tracking-tight">
            Chaos Engineering & Outage Simulation Deck
          </h2>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Autonomous Heal Button */}
          <button
            onClick={onAutonomousHeal}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-mono text-xs font-semibold shadow-neon-green transition-all disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4 text-emerald-200" />
            <span>Autonomous Heal (Bedrock Agent)</span>
          </button>

          {/* Reset button */}
          <button
            onClick={onReset}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-mono text-xs transition-all disabled:opacity-50"
          >
            <RefreshCcw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Scenario Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          return (
            <div
              key={sc.id}
              className={`flex flex-col justify-between rounded-lg border border-slate-800/90 bg-slate-900/40 p-4 transition-all duration-200 ${sc.color}`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span className="font-mono text-sm font-bold text-slate-100">{sc.title}</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-950/70 border border-rose-800 text-rose-300">
                    {sc.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-sans leading-relaxed mb-4">
                  {sc.description}
                </p>
              </div>

              <button
                onClick={() => onInjectChaos(sc.id)}
                disabled={loading}
                className="flex items-center justify-center gap-1.5 w-full py-1.5 px-3 rounded-md bg-slate-800/80 hover:bg-rose-950/70 hover:border-rose-600 active:bg-rose-900 border border-slate-700 text-slate-200 font-mono text-xs transition-colors disabled:opacity-50"
              >
                <Play className="w-3 h-3 text-rose-400" />
                <span>Inject Chaos</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
