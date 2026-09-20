"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, AlertTriangle, RefreshCw, Cpu, Cloud, CheckCircle, Copy, Check } from "lucide-react";
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
    <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <Cloud className="w-6 h-6 animate-pulse" />
            <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-1.5">
                StrandsOps <span className="text-emerald-400 font-mono text-sm px-1.5 py-0.5 rounded bg-emerald-950/70 border border-emerald-800">SRE</span>
              </h1>
              <span className="text-[10px] uppercase font-mono tracking-widest px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-800/80 text-cyan-300">
                Autonomous Bedrock Agent
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Self-Healing Cloud Infrastructure & Two-Tier Triage
            </p>
          </div>
        </div>

        {/* AWS & Model Badges */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
          {/* AWS Account ID */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-900/90 border border-slate-700/70 text-slate-300">
            <span className="text-slate-400">AWS:</span>
            <span className="text-amber-400 font-semibold tracking-wider">3792-6468-7588</span>
            <button
              onClick={handleCopyAccount}
              title="Copy AWS Account ID"
              className="ml-1 text-slate-400 hover:text-white transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Region */}
          <div className="px-2.5 py-1.5 rounded-md bg-slate-900/90 border border-slate-700/70 text-slate-300 flex items-center gap-1">
            <span className="text-slate-500">Region:</span>
            <span className="text-cyan-400">us-east-1</span>
          </div>

          {/* Bedrock Model */}
          <div className="px-2.5 py-1.5 rounded-md bg-slate-900/90 border border-slate-700/70 text-slate-300 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-purple-300">Bedrock Claude 3.5 Sonnet</span>
          </div>

          {/* Cluster Status Badge */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md border font-semibold ${
              isIncident
                ? "bg-rose-950/70 border-rose-600 text-rose-300 shadow-neon-rose"
                : isRemediating
                ? "bg-amber-950/70 border-amber-600 text-amber-300 shadow-neon-amber"
                : "bg-emerald-950/70 border-emerald-600 text-emerald-300 shadow-neon-green"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isIncident
                  ? "bg-rose-500 animate-ping"
                  : isRemediating
                  ? "bg-amber-500 animate-pulse"
                  : "bg-emerald-500"
              }`}
            />
            <span>{status}</span>
          </div>

          {/* Clock */}
          <div className="hidden lg:block text-slate-400 text-[11px] px-2">
            {time}
          </div>

          {/* Reset button */}
          <button
            onClick={onReset}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 active:bg-slate-900 border border-slate-600 text-slate-200 text-xs transition-colors disabled:opacity-50"
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
