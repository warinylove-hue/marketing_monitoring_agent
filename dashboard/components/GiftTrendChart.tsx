"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatWon } from "@/lib/money";
import type { TrendPoint } from "@/types/dashboard";

const SITE_COLORS: Record<string, string> = {
  아정당: "#2563eb",
  MISO: "#16a34a",
  "U+": "#dc2626",
  KT: "#7c3aed",
  SKB: "#ea580c",
  SKT: "#0f766e",
};

export function GiftTrendChart({ data }: { data: TrendPoint[] }) {
  const siteNames = Object.keys(SITE_COLORS);

  return (
    <div className="h-[390px] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-blue-600">Gift Trend</p>
          <h2 className="text-xl font-black text-slate-950">사이트별 최고 사은품 변동 추이</h2>
          <p className="mt-1 text-sm text-slate-500">
            날짜별 각 사이트의 최고 사은품 금액을 비교합니다.
          </p>
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">
          Recharts
        </span>
      </div>
      {data.length ? (
      <ResponsiveContainer width="100%" height="72%">
        <LineChart data={data} margin={{ left: 8, right: 24, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#64748b" />
          <YAxis
            tick={{ fontSize: 12 }}
            stroke="#64748b"
            tickFormatter={(value) => `${Number(value) / 10000}만`}
          />
          <Tooltip
            formatter={(value) => formatWon(Number(value))}
            contentStyle={{
              borderRadius: 16,
              border: "1px solid #e2e8f0",
              boxShadow: "0 20px 45px rgba(15, 23, 42, 0.12)",
            }}
          />
          <Legend />
          {siteNames.map((siteName) => (
            <Line
              key={siteName}
              type="monotone"
              dataKey={siteName}
              stroke={SITE_COLORS[siteName]}
              strokeWidth={3}
              dot={{ r: 3 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      ) : (
        <div className="flex h-[260px] items-center justify-center rounded-2xl bg-slate-50 text-sm text-slate-500">
          차트로 표시할 데이터가 없습니다.
        </div>
      )}
    </div>
  );
}
