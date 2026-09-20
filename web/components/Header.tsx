"use client";

import React, { useEffect, useState } from "react";
import { RefreshCw, Cpu, Hexagon, Copy, Check } from "lucide-react";
import { ClusterState } from "@/lib/engine";
import { APP_CONFIG } from "@/lib/config";

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
      setTime(now.toISOString().replace("T", " ").substring(11, 19) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCopyAccount = () => {
    navigator.clipboard.writeText(APP_CONFIG.awsAccountId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const status = clusterState?.status || "NORMAL";
  const isIncident = status === "INCIDENT";
  const isRemediating = status === "REMEDIATING";

  return (
    <header className="sticky top-0 z-50 border-b border-brand/15 bg-[#050a14]/85 backdrop-blur-xl px-4 sm:px-6 py-2.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Left Side: Brand Logo & Title */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-brand/40 bg-brand/15 text-brand-bright shadow-neon-blue">
            <Hexagon className="w-5 h-5" strokeWidth={1.75} />
            <div className="absolute inset-0 rounded-xl bg-brand/20 blur-md -z-10" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-base font-bold text-white tracking-tight">
                StrandsOps
              </h1>
              <span className="text-[10px] uppercase tracking-[0.14em] px-1.5 py-0.5 rounded-md border border-brand/35 bg-brand/10 text-brand-soft font-semibold">
                SRE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Investigate · Check risk · Fix · Re-verify
            </p>
          </div>
        </div>

        {/* Center: Navigation Links */}
        <nav className="hidden lg:flex items-center gap-6 text-xs font-medium text-slate-400">
          <a href="#chaos" className="hover:text-brand-bright transition-colors">
            Chaos Lab
          </a>
          <a href="#map" className="hover:text-brand-bright transition-colors">
            Service Map
          </a>
          <a href="#console" className="hover:text-brand-bright transition-colors">
            Triage Console
          </a>
        </nav>

        {/* Right Side: AWS Metadata, Status, and Controls (Strictly Single Row) */}
        <div className="flex items-center gap-2 shrink-0 text-xs">
          {/* AWS Account ID Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-brand/20 bg-brand-muted/40 text-slate-300">
            <span className="text-slate-500 font-medium">AWS</span>
            <span className="text-amber-300 font-semibold font-mono tracking-wide">
              {APP_CONFIG.awsAccountId}
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

          {/* Region Badge */}
          <div className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-brand/20 bg-brand-muted/40 text-slate-300">
            <span className="text-slate-500">Region</span>
            <span className="text-brand-soft font-mono font-medium">{APP_CONFIG.awsRegion}</span>
          </div>

          {/* Bedrock Model Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-purple-500/30 bg-purple-950/40 text-purple-300">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="font-medium">Claude 3.5 Sonnet</span>
          </div>

          {/* Cluster Status Pill */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-semibold ${
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
            <span className="font-mono text-[11px]">{status}</span>
          </div>

          {/* Clock */}
          <div className="hidden xl:block text-slate-500 font-mono text-[11px] px-1">
            {time}
          </div>

          {/* Reset Cluster Button */}
          <button
            onClick={onReset}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700/80 bg-slate-800/80 hover:bg-slate-700/90 text-slate-200 text-xs font-medium transition-colors disabled:opacity-50"
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
