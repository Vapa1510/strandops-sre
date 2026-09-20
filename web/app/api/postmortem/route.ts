import { NextResponse } from "next/server";
import { getClusterState, generatePostmortem } from "@/lib/engine";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = getClusterState();
  if (state.postmortem) {
    return NextResponse.json({ postmortem: state.postmortem });
  }
  if (state.active_incident) {
    const postmortem = generatePostmortem(state.active_incident);
    return NextResponse.json({ postmortem });
  }
  return NextResponse.json({
    postmortem: "# NO RECENT INCIDENT POSTMORTEM\n\nCluster is in nominal state. Run a chaos test to trigger an incident and postmortem analysis.",
  });
}
