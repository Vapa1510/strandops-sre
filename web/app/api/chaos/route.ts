import { NextResponse } from "next/server";
import { injectChaos, resetCluster } from "@/lib/engine";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, scenario } = body;

    if (action === "reset") {
      const state = resetCluster();
      return NextResponse.json({ success: true, message: "Cluster reset to baseline", state });
    }

    if (action === "inject" && scenario) {
      const validScenarios = ["poison_pill", "connection_leak", "circuit_breaker_trip", "bad_deployment"];
      if (!validScenarios.includes(scenario)) {
        return NextResponse.json({ error: `Invalid scenario. Must be one of ${validScenarios.join(", ")}` }, { status: 400 });
      }
      const state = injectChaos(scenario);
      return NextResponse.json({ success: true, message: `Injected ${scenario}`, state });
    }

    return NextResponse.json({ error: "Invalid action. Must provide 'action': 'inject' | 'reset'" }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
