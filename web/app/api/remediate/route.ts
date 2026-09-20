import { NextResponse } from "next/server";
import { executeRemediation } from "@/lib/engine";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, target } = body;

    if (!action || !target) {
      return NextResponse.json({ error: "Missing required fields 'action' and 'target'" }, { status: 400 });
    }

    const result = executeRemediation(action, target);
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
