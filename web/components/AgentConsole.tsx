"use client";

import React, { useState } from "react";
import { Terminal, Send, CheckCircle2, ShieldCheck, AlertTriangle, Cpu, Zap, FileText, ArrowRight } from "lucide-react";
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
        return <Cpu className="w-4 h-4 text-purple-400" />;
      case "SAFETY_CHECK":
        return <ShieldCheck className="w-4 h-4 text-amber-400" />;
      case "REMEDIATE":
        return <Zap className="w-4 h-4 text-cyan-400" />;
      case "VERIFY":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/70 p-5 backdrop-blur-md flex flex-col h-[520px]">
      {/* Console Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h2 className="text-base font-bold text-slate-100 font-mono tracking-tight">
            Autonomous SRE Reasoning Loop & Two-Tier Console
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {hasPostmortem && (
            <button
              onClick={onOpenPostmortem}
              className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-purple-950/80 hover:bg-purple-900 border border-purple-700 text-purple-300 font-mono text-xs transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>View Incident Postmortem</span>
            </button>
          )}

          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <span className="px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
              Tier-0 Cache (&lt;5ms)
            </span>
            <span className="px-2 py-0.5 rounded bg-purple-950/70 border border-purple-800 text-purple-300">
              Tier-2 Bedrock Sonnet
            </span>
          </div>
        </div>
      </div>

      {/* Steps & Activity Stream */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 font-mono text-xs">
        {steps.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
            <Terminal className="w-8 h-8 opacity-30 text-cyan-400" />
            <p>Agent standing by. Inject chaos or send a prompt to observe the 5-step triage loop.</p>
          </div>
        ) : (
          steps.map((step, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3.5 transition-all"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  {getStepIcon(step.step)}
                  <span className="font-bold text-slate-200">
                    [{idx + 1}/5] {step.step}
                  </span>
                  <span className="text-slate-400">&bull;</span>
                  <span className="text-slate-100 font-semibold">{step.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${
                      step.tier === "TIER_0_CACHE"
                        ? "bg-emerald-950/80 border-emerald-700 text-emerald-300"
                        : "bg-purple-950/80 border-purple-700 text-purple-300"
                    }`}
                  >
                    {step.tier === "TIER_0_CACHE" ? "Tier-0 Cache" : "Tier-2 Bedrock"}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {step.timestamp.slice(11, 19)}
                  </span>
                </div>
              </div>
              <p className="text-slate-300 font-sans text-xs pl-6 leading-relaxed">
                {step.details}
              </p>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-3 p-3 rounded-lg border border-cyan-500/30 bg-cyan-950/20 text-cyan-300">
            <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span>AI SRE Agent synthesizing AWS telemetry & evaluating blast-radius guardrails...</span>
          </div>
        )}

        {remediationSummary && !loading && (
          <div className="p-3.5 rounded-lg border border-emerald-500/40 bg-emerald-950/30 text-emerald-300">
            <div className="font-bold flex items-center gap-1.5 mb-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Incident Remediated & Soak-Verified</span>
            </div>
            <p className="text-xs text-slate-300 font-sans">{remediationSummary}</p>
          </div>
        )}
      </div>

      {/* Query Form */}
      <form onSubmit={handleSubmit} className="pt-3 mt-2 border-t border-white/10 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Issue natural language command to SRE Agent (e.g. 'Investigate payment gateway latency' or 'Scale worker to 4x')..."
          disabled={loading}
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 text-white text-xs font-mono font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Dispatch</span>
        </button>
      </form>
    </div>
  );
}
