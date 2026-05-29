import { formatWon } from "@/lib/money";
import type { DashboardKpis, SiteSummary } from "@/types/dashboard";

export function SummaryCards({
  latestDate,
  kpis,
  summaries,
}: {
  latestDate: string;
  kpis: DashboardKpis;
  summaries: SiteSummary[];
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card label="최신 수집일" value={latestDate || "-"} subText="Google Sheet 기준" tone="blue" />
      <Card
        label="최신 수집 행"
        value={`${kpis.latestRowCount.toLocaleString("ko-KR")}건`}
        subText={`${kpis.activeSiteCount}개 사이트 반영`}
        tone="slate"
      />
      <Card
        label="최고 사은품"
        value={kpis.maxGiftWon ? `${kpis.maxGiftSite} ${formatWon(kpis.maxGiftWon)}` : "-"}
        subText={kpis.maxGiftProduct || "최신 수집일 기준"}
        tone="emerald"
      />
      <Card
        label="평균 사은품"
        value={formatWon(kpis.averageGiftWon)}
        subText={`누적 ${kpis.totalRows.toLocaleString("ko-KR")}건`}
        tone="violet"
      />
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm md:col-span-2 xl:col-span-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-500">Site Coverage</p>
            <h2 className="text-lg font-black text-slate-950">사이트별 최신 수집 상태</h2>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
            6개 사이트
          </span>
        </div>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {summaries.map((site) => (
            <div key={site.siteName} className="rounded-2xl bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <p className="font-black text-slate-950">{site.siteName}</p>
                <span className="text-xs font-bold text-slate-500">{site.latestRowCount}건</span>
              </div>
              <p className="mt-2 text-sm font-bold text-emerald-700">
                {formatWon(site.maxGiftWon)}
              </p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                {site.bestProductLabel}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Card({
  label,
  value,
  subText,
  tone,
}: {
  label: string;
  value: string;
  subText: string;
  tone: "blue" | "emerald" | "slate" | "violet";
}) {
  const toneClasses = {
    blue: "from-blue-50 to-white text-blue-600",
    emerald: "from-emerald-50 to-white text-emerald-600",
    slate: "from-slate-50 to-white text-slate-600",
    violet: "from-violet-50 to-white text-violet-600",
  }[tone];

  return (
    <div className={`rounded-3xl border border-slate-200 bg-gradient-to-br p-6 shadow-sm ${toneClasses}`}>
      <p className="text-sm font-black">{label}</p>
      <p className="mt-3 text-2xl font-black tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 line-clamp-2 text-sm text-slate-500">{subText}</p>
    </div>
  );
}
