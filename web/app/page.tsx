"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { TopologyMap } from "@/components/TopologyMap";
import { ChaosDeck } from "@/components/ChaosDeck";
import { AgentConsole } from "@/components/AgentConsole";
import { TelemetryTable } from "@/components/TelemetryTable";
import { ActionDrawer } from "@/components/ActionDrawer";
import { PostmortemModal } from "@/components/PostmortemModal";
import { ClusterState, AgentStep } from "@/lib/engine";

export default function Home() {
  const [clusterState, setClusterState] = useState<ClusterState | null>(null);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [remediationSummary, setRemediationSummary] = useState<string | null>(null);
  const [postmortemMarkdown, setPostmortemMarkdown] = useState<string>("");
  const [isPostmortemOpen, setIsPostmortemOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedService, setSelectedService] = useState<string | null>(null);

  // Fetch live telemetry polling
  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch("/api/telemetry");
      if (res.ok) {
        const data: ClusterState = await res.json();
        setClusterState(data);
        if (data.postmortem) {
          setPostmortemMarkdown(data.postmortem);
        }
      }
    } catch (err) {
      console.error("Telemetry fetch failed:", err);
    }
  }, []);

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2500);
    return () => clearInterval(interval);
  }, [fetchTelemetry]);

  // Inject Chaos Scenario
  const handleInjectChaos = async (
    scenario: "poison_pill" | "connection_leak" | "circuit_breaker_trip" | "bad_deployment"
  ) => {
    setLoading(true);
    try {
      const res = await fetch("/api/chaos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "inject", scenario }),
      });
      if (res.ok) {
        const data = await res.json();
        setClusterState(data.state);
        setRemediationSummary(null);
        setAgentSteps([]);
      }
    } catch (err) {
      console.error("Chaos injection failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // Autonomous Heal via Bedrock Agent
  const handleAutonomousHeal = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "Autonomous heal active cluster incident" }),
      });
      if (res.ok) {
        const data = await res.json();
        setAgentSteps(data.steps || []);
        setRemediationSummary(data.remediationSummary || null);
        if (data.postmortem) {
          setPostmortemMarkdown(data.postmortem);
        }
        await fetchTelemetry();
      }
    } catch (err) {
      console.error("Autonomous heal failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // Reset Cluster
  const handleReset = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/chaos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "reset" }),
      });
      if (res.ok) {
        const data = await res.json();
        setClusterState(data.state);
        setAgentSteps([]);
        setRemediationSummary(null);
        setPostmortemMarkdown("");
      }
    } catch (err) {
      console.error("Reset failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // Submit Natural Language Query to SRE Agent
  const handleSubmitQuery = async (query: string) => {
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (res.ok) {
        const data = await res.json();
        setAgentSteps(data.steps || []);
        setRemediationSummary(data.remediationSummary || null);
        if (data.postmortem) {
          setPostmortemMarkdown(data.postmortem);
        }
        await fetchTelemetry();
      }
    } catch (err) {
      console.error("Agent query failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // Manual Remediate Action
  const handleExecuteAction = async (action: string, target: string) => {
    try {
      const res = await fetch("/api/remediate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, target }),
      });
      const data = await res.json();
      if (data.state) {
        setClusterState(data.state);
      }
      return data;
    } catch (err) {
      console.error("Manual action failed:", err);
      return { success: false, message: "Action execution failed." };
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Header */}
      <Header
        clusterState={clusterState}
        onReset={handleReset}
        loading={loading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Chaos Engineering Deck */}
        <ChaosDeck
          onInjectChaos={handleInjectChaos}
          onAutonomousHeal={handleAutonomousHeal}
          onReset={handleReset}
          loading={loading}
          hasActiveIncident={clusterState?.status === "INCIDENT"}
        />

        {/* Microservice Topology Canvas */}
        {clusterState && (
          <TopologyMap
            services={clusterState.services}
            queue={clusterState.queue}
            selectedService={selectedService}
            onSelectService={(s) => setSelectedService(s)}
          />
        )}

        {/* Grid: Autonomous Reasoning Console + Live SLA Table */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6">
            <AgentConsole
              steps={agentSteps}
              remediationSummary={remediationSummary}
              loading={loading}
              onSubmitQuery={handleSubmitQuery}
              onOpenPostmortem={() => setIsPostmortemOpen(true)}
              hasPostmortem={Boolean(postmortemMarkdown)}
            />
          </div>

          <div className="lg:col-span-6 space-y-6">
            {clusterState && <TelemetryTable services={clusterState.services} />}
            {clusterState && (
              <ActionDrawer
                services={clusterState.services}
                onExecuteAction={handleExecuteAction}
                loading={loading}
              />
            )}
          </div>
        </div>
      </main>

      {/* Postmortem Modal */}
      <PostmortemModal
        isOpen={isPostmortemOpen}
        onClose={() => setIsPostmortemOpen(false)}
        markdown={postmortemMarkdown}
      />

      {/* Footer */}
      <footer className="border-t border-white/10 bg-slate-950/80 px-4 py-3 text-center text-xs font-mono text-slate-500">
        StrandsOps SRE &bull; Amazon Bedrock Claude 3.5 Sonnet &bull; AWS Account ID 3792-6468-7588 &bull; WeMakeDevs Bharat Builds 2026
      </footer>
    </div>
  );
}
