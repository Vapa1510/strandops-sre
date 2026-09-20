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
    postmortem: "# No recent postmortem\n\nCluster looks healthy. Stage an outage in the chaos lab, run triage, then open a write-up.",
  });
}
