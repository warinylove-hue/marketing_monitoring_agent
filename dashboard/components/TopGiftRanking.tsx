import { formatWon } from "@/lib/money";
import type { TopGiftItem } from "@/types/dashboard";

export function TopGiftRanking({ items }: { items: TopGiftItem[] }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-blue-200">Executive Ranking</p>
          <h2 className="text-xl font-black">오늘 최고 사은품 TOP 5</h2>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-black text-slate-200">
          최신 수집일 기준
        </span>
      </div>

      <div className="space-y-3">
        {items.slice(0, 5).map((item) => (
          <div key={`${item.rank}-${item.siteName}-${item.productLabel}`} className="rounded-2xl bg-white/10 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500 text-xs font-black">
                    {item.rank}
                  </span>
                  <p className="font-black">{item.siteName}</p>
                  <p className="text-sm text-slate-300">{item.carrierName}</p>
                </div>
                <p className="mt-2 line-clamp-2 text-sm leading-5 text-slate-200">
                  {item.productLabel}
                </p>
                <p className="mt-1 text-xs text-slate-400">기본 요금 {item.baseFee || "-"}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-lg font-black text-emerald-300">
                  {item.giftAmount || formatWon(item.giftAmountWon)}
                </p>
                <p className="text-xs text-slate-400">사은품</p>
              </div>
            </div>
          </div>
        ))}
        {!items.length ? (
          <div className="rounded-2xl bg-white/10 p-6 text-center text-sm text-slate-300">
            사은품 순위를 계산할 데이터가 없습니다.
          </div>
        ) : null}
      </div>
    </div>
  );
}
