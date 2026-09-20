import { NextResponse } from "next/server";
import { getClusterState } from "@/lib/engine";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = getClusterState();
  return NextResponse.json(state);
}
