"use client";

import React, { useEffect, useState } from "react";
import { RefreshCw, Cpu, Hexagon, Copy, Check } from "lucide-react";
import { ClusterState } from "@/lib/engine";

interface HeaderProps {
  clusterState: ClusterState | null;
  onReset: () => void;
  loading: boolean;
}

export function Header({ clusterState, onReset, loading }: HeaderProps) {
  const [copied, setCopied] = useState(false);
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toISOString().replace("T", " ").substring(0, 19) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCopyAccount = () => {
    navigator.clipboard.writeText("3792-6468-7588");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const status = clusterState?.status || "NORMAL";
  const isIncident = status === "INCIDENT";
  const isRemediating = status === "REMEDIATING";

  return (
    <header className="sticky top-0 z-50 border-b border-brand/15 bg-[#050a14]/75 backdrop-blur-xl px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-brand/40 bg-brand/15 text-brand-bright shadow-neon-blue">
            <Hexagon className="w-6 h-6" strokeWidth={1.75} />
            <div className="absolute inset-0 rounded-xl bg-brand/20 blur-md -z-10" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-display text-lg font-bold text-white tracking-tight">
                StrandsOps
              </h1>
              <span className="text-[10px] uppercase tracking-[0.14em] px-2 py-0.5 rounded-md border border-brand/35 bg-brand/10 text-brand-soft font-semibold">
                SRE
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Investigate · Check risk · Fix · Re-verify
            </p>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-5 text-sm text-slate-400">
          <a href="#chaos" className="hover:text-white transition-colors">
            Chaos lab
          </a>
          <a href="#map" className="hover:text-white transition-colors">
            Service map
          </a>
          <a href="#console" className="hover:text-white transition-colors">
            Triage
          </a>
        </nav>

        <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand/20 bg-brand-muted/40 text-slate-300">
            <span className="text-slate-500">AWS</span>
            <span className="text-amber-300 font-semibold tracking-wider font-mono">
              3792-6468-7588
            </span>
            <button
              onClick={handleCopyAccount}
              title="Copy AWS Account ID"
              className="ml-0.5 text-slate-400 hover:text-white transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>

          <div className="px-2.5 py-1.5 rounded-xl border border-brand/20 bg-brand-muted/40 text-slate-300">
            <span className="text-slate-500">Region </span>
            <span className="text-brand-soft font-medium">us-east-1</span>
          </div>

          <div className="px-2.5 py-1.5 rounded-xl border border-brand/20 bg-brand-muted/40 text-slate-300 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-brand-bright" />
            <span>Ready for triage</span>
          </div>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border font-semibold ${
              isIncident
                ? "bg-rose-950/60 border-rose-500/50 text-rose-300 shadow-neon-rose"
                : isRemediating
                ? "bg-amber-950/60 border-amber-500/50 text-amber-300 shadow-neon-amber"
                : "bg-emerald-950/50 border-emerald-500/40 text-emerald-300 shadow-neon-green"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isIncident
                  ? "bg-rose-500 animate-ping"
                  : isRemediating
                  ? "bg-amber-500 animate-pulse"
                  : "bg-emerald-400"
              }`}
            />
            <span className="font-mono">{status}</span>
          </div>

          <div className="hidden xl:block text-slate-500 font-mono text-[11px] px-1">
            {time}
          </div>

          <button
            onClick={onReset}
            disabled={loading}
            className="btn-ghost !py-1.5 !px-3 !text-xs"
            title="Reset Cluster to Baseline"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reset</span>
          </button>
        </div>
      </div>
    </header>
  );
}
