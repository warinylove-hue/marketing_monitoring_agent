import { NextResponse } from "next/server";

import { getDashboardData } from "@/lib/dashboardData";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const data = await getDashboardData();
    return NextResponse.json(data);
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "대시보드 데이터를 불러오지 못했습니다.",
      },
      { status: 500 },
    );
  }
}
