"use client";

import React, { useState } from "react";
import { Wrench, Play, ShieldAlert, CheckCircle, XCircle } from "lucide-react";
import { ServiceMetrics } from "@/lib/engine";

interface ActionDrawerProps {
  services: Record<string, ServiceMetrics>;
  onExecuteAction: (action: string, target: string) => Promise<any>;
  loading: boolean;
}

export function ActionDrawer({ services, onExecuteAction, loading }: ActionDrawerProps) {
  const [selectedTarget, setSelectedTarget] = useState<string>("order-service");
  const [selectedAction, setSelectedAction] = useState<string>("flush_connection_pool");
  const [actionResult, setActionResult] = useState<{ success: boolean; message: string } | null>(null);

  const actions = [
    { id: "flush_connection_pool", label: "Flush Connection Pool", target: "order-service" },
    { id: "rollback_deployment", label: "Rollback Deployment to Stable (v2.4.1)", target: "api-gateway" },
    { id: "isolate_poison_pill", label: "Isolate SQS Poison Pill", target: "order-processing-queue" },
    { id: "purge_dlq", label: "Purge Dead-Letter Queue (DLQ)", target: "order-processing-dlq" },
    { id: "reset_circuit_breaker", label: "Reset Circuit Breaker (to CLOSED)", target: "order-service" },
    { id: "scale_replicas", label: "Scale Service Replicas (+2)", target: "inventory-worker" },
    { id: "restart_service", label: "Graceful Container Restart", target: "api-gateway" },
  ];

  const handleExecute = async () => {
    setActionResult(null);
    const res = await onExecuteAction(selectedAction, selectedTarget);
    if (res) {
      setActionResult({
        success: res.success,
        message: res.message || (res.success ? "Action executed successfully." : "Action blocked by safety policy."),
      });
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-5 backdrop-blur-md">
      <div className="flex items-center gap-2 mb-4">
        <Wrench className="w-5 h-5 text-amber-400" />
        <h2 className="text-base font-bold text-slate-100 font-mono tracking-tight">
          Manual SRE Runbook Dispatcher
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {/* Action Selector */}
        <div>
          <label className="block text-xs font-mono text-slate-400 mb-1.5">Remediation Primitive</label>
          <select
            value={selectedAction}
            onChange={(e) => {
              const act = e.target.value;
              setSelectedAction(act);
              const found = actions.find((a) => a.id === act);
              if (found) setSelectedTarget(found.target);
            }}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500"
          >
            {actions.map((act) => (
              <option key={act.id} value={act.id}>
                {act.label}
              </option>
            ))}
          </select>
        </div>

        {/* Target Selector */}
        <div>
          <label className="block text-xs font-mono text-slate-400 mb-1.5">Target Resource</label>
          <input
            type="text"
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500"
          />
        </div>

        {/* Dispatch Button */}
        <div className="flex items-end">
          <button
            onClick={handleExecute}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 active:bg-amber-700 text-white font-mono text-xs font-semibold shadow-neon-amber transition-all disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Execute Primitive</span>
          </button>
        </div>
      </div>

      {/* Execution Feedback */}
      {actionResult && (
        <div
          className={`p-3 rounded-lg border flex items-center gap-2 font-mono text-xs ${
            actionResult.success
              ? "border-emerald-500/40 bg-emerald-950/30 text-emerald-300"
              : "border-rose-500/40 bg-rose-950/30 text-rose-300"
          }`}
        >
          {actionResult.success ? (
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{actionResult.message}</span>
        </div>
      )}
    </div>
  );
}
