import { NextResponse } from "next/server";
import { runAutonomousTriage } from "@/lib/engine";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const query = body.query || "Investigate cluster health and remediate any SLA breaches.";
    const result = runAutonomousTriage(query);
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
