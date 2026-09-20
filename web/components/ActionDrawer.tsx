"use client";

import React, { useState } from "react";
import { Wrench, Play, CheckCircle, XCircle } from "lucide-react";
import { ServiceMetrics } from "@/lib/engine";

interface ActionDrawerProps {
  services: Record<string, ServiceMetrics>;
  onExecuteAction: (action: string, target: string) => Promise<any>;
  loading: boolean;
}

export function ActionDrawer({ onExecuteAction, loading }: ActionDrawerProps) {
  const [selectedTarget, setSelectedTarget] = useState<string>("order-service");
  const [selectedAction, setSelectedAction] = useState<string>("flush_connection_pool");
  const [actionResult, setActionResult] = useState<{ success: boolean; message: string } | null>(
    null
  );

  const actions = [
    { id: "flush_connection_pool", label: "Flush Connection Pool", target: "order-service" },
    {
      id: "rollback_deployment",
      label: "Rollback Deployment to Stable (v2.4.1)",
      target: "api-gateway",
    },
    {
      id: "isolate_poison_pill",
      label: "Isolate SQS Poison Pill",
      target: "order-processing-queue",
    },
    { id: "purge_dlq", label: "Purge Dead-Letter Queue (DLQ)", target: "order-processing-dlq" },
    {
      id: "reset_circuit_breaker",
      label: "Reset Circuit Breaker (to CLOSED)",
      target: "order-service",
    },
    { id: "scale_replicas", label: "Scale Service Replicas (+2)", target: "inventory-worker" },
    { id: "restart_service", label: "Graceful Container Restart", target: "api-gateway" },
  ];

  const handleExecute = async () => {
    setActionResult(null);
    const res = await onExecuteAction(selectedAction, selectedTarget);
    if (res) {
      setActionResult({
        success: res.success,
        message:
          res.message ||
          (res.success ? "Action executed successfully." : "Action blocked by safety policy."),
      });
    }
  };

  return (
    <div className="glass-panel p-5">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10">
          <Wrench className="w-4 h-4 text-amber-400" />
        </div>
        <h2 className="font-display text-base font-bold text-white tracking-tight">
          Manual runbook
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Action</label>
          <select
            value={selectedAction}
            onChange={(e) => {
              const act = e.target.value;
              setSelectedAction(act);
              const found = actions.find((a) => a.id === act);
              if (found) setSelectedTarget(found.target);
            }}
            className="input-glass font-mono"
          >
            {actions.map((act) => (
              <option key={act.id} value={act.id}>
                {act.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Target resource</label>
          <input
            type="text"
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value)}
            className="input-glass font-mono"
          />
        </div>

        <div className="flex items-end">
          <button
            onClick={handleExecute}
            disabled={loading}
            className="w-full btn-brand !bg-gradient-to-r !from-amber-500 !to-amber-600 hover:!from-amber-400 hover:!to-amber-500 !shadow-[0_0_24px_-6px_rgba(245,158,11,0.55)] !text-xs"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Run action</span>
          </button>
        </div>
      </div>

      {actionResult && (
        <div
          className={`p-3 rounded-xl border flex items-center gap-2 text-xs ${
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
          <span className="font-mono">{actionResult.message}</span>
        </div>
      )}
    </div>
  );
}
