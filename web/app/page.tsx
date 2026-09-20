"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { HeroStrip } from "@/components/HeroStrip";
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
  const chaosRef = useRef<HTMLDivElement>(null);

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

  const handleAutonomousHeal = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "Investigate the active incident, check blast radius, fix, and re-verify",
        }),
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
      console.error("Triage failed:", err);
    } finally {
      setLoading(false);
    }
  };

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
    <div className="min-h-screen flex flex-col">
      <Header clusterState={clusterState} onReset={handleReset} loading={loading} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pb-10 space-y-6">
        <HeroStrip
          clusterState={clusterState}
          onRunTriage={handleAutonomousHeal}
          onScrollToChaos={() =>
            chaosRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
          }
          loading={loading}
        />

        <div ref={chaosRef}>
          <ChaosDeck
            onInjectChaos={handleInjectChaos}
            onAutonomousHeal={handleAutonomousHeal}
            onReset={handleReset}
            loading={loading}
            hasActiveIncident={clusterState?.status === "INCIDENT"}
          />
        </div>

        {clusterState && (
          <TopologyMap
            services={clusterState.services}
            queue={clusterState.queue}
            selectedService={selectedService}
            onSelectService={(s) => setSelectedService(s)}
          />
        )}

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

      <PostmortemModal
        isOpen={isPostmortemOpen}
        onClose={() => setIsPostmortemOpen(false)}
        markdown={postmortemMarkdown}
      />

      <footer className="border-t border-brand/15 bg-[#050a14]/80 backdrop-blur-md px-4 py-4 text-center text-xs text-slate-500">
        StrandsOps SRE · On-call incident helper · AWS Account 3792-6468-7588 · WeMakeDevs Bharat
        Builds 2026
      </footer>
    </div>
  );
}
