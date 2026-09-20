"use client";

import React, { useState } from "react";
import {
  Terminal,
  Send,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  Cpu,
  Zap,
  FileText,
} from "lucide-react";
import { AgentStep } from "@/lib/engine";

interface AgentConsoleProps {
  steps: AgentStep[];
  remediationSummary: string | null;
  loading: boolean;
  onSubmitQuery: (query: string) => void;
  onOpenPostmortem: () => void;
  hasPostmortem: boolean;
}

export function AgentConsole({
  steps,
  remediationSummary,
  loading,
  onSubmitQuery,
  onOpenPostmortem,
  hasPostmortem,
}: AgentConsoleProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSubmitQuery(input.trim());
    setInput("");
  };

  const getStepIcon = (step: AgentStep["step"]) => {
    switch (step) {
      case "DETECT":
        return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case "DIAGNOSE":
        return <Cpu className="w-4 h-4 text-brand-bright" />;
      case "SAFETY_CHECK":
        return <ShieldCheck className="w-4 h-4 text-amber-400" />;
      case "REMEDIATE":
        return <Zap className="w-4 h-4 text-cyan-400" />;
      case "VERIFY":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    }
  };

  return (
    <div
      id="console"
      className="glass-panel p-5 flex flex-col h-[520px] scroll-mt-24"
    >
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-brand/15">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-brand/30 bg-brand/10">
            <Terminal className="w-4 h-4 text-brand-bright" />
          </div>
          <h2 className="font-display text-base font-bold text-white tracking-tight">
            On-call triage
          </h2>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {hasPostmortem && (
            <button
              onClick={onOpenPostmortem}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg border border-brand/35 bg-brand/15 hover:bg-brand/25 text-brand-soft text-xs font-medium transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Postmortem</span>
            </button>
          )}

          <div className="flex items-center gap-1.5 text-[10px]">
            <span className="px-2 py-0.5 rounded-md bg-emerald-950/70 border border-emerald-800/80 text-emerald-300">
              Playbook
            </span>
            <span className="px-2 py-0.5 rounded-md bg-brand/15 border border-brand/35 text-brand-soft">
              Investigate
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
        {steps.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
            <Terminal className="w-8 h-8 opacity-30 text-brand-bright" />
            <p className="text-center max-w-xs">
              Standing by. Stage an outage above, or describe what looks wrong.
            </p>
          </div>
        ) : (
          steps.map((step, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-brand/15 bg-[#071225]/80 p-3.5"
            >
              <div className="flex items-center justify-between mb-1.5 gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  {getStepIcon(step.step)}
                  <span className="font-mono font-bold text-slate-200">
                    [{idx + 1}/5] {step.step}
                  </span>
                  <span className="text-slate-500">·</span>
                  <span className="text-slate-100 font-semibold">{step.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${
                      step.tier === "TIER_0_CACHE"
                        ? "bg-emerald-950/80 border-emerald-700 text-emerald-300"
                        : "bg-brand/20 border-brand/40 text-brand-soft"
                    }`}
                  >
                    {step.tier === "TIER_0_CACHE" ? "Playbook" : "Investigate"}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {step.timestamp.slice(11, 19)}
                  </span>
                </div>
              </div>
              <p className="text-slate-300 text-xs pl-6 leading-relaxed">{step.details}</p>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-3 p-3 rounded-xl border border-brand/30 bg-brand/10 text-brand-soft">
            <div className="w-4 h-4 border-2 border-brand-bright border-t-transparent rounded-full animate-spin" />
            <span>Reading telemetry and checking blast-radius limits...</span>
          </div>
        )}

        {remediationSummary && !loading && (
          <div className="p-3.5 rounded-xl border border-emerald-500/35 bg-emerald-950/25 text-emerald-300">
            <div className="font-semibold flex items-center gap-1.5 mb-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Fixed — metrics re-checked</span>
            </div>
            <p className="text-xs text-slate-300">{remediationSummary}</p>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="pt-3 mt-2 border-t border-brand/15 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Investigate payment latency, or scale inventory-worker..."
          disabled={loading}
          className="input-glass font-mono"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="btn-brand !px-4 !text-xs shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
