"use client";

import { useMemo, useState } from "react";

import type { CrawlRow } from "@/types/dashboard";

export function DataTable({ rows }: { rows: CrawlRow[] }) {
  const [siteFilter, setSiteFilter] = useState("전체");
  const [productFilter, setProductFilter] = useState("전체");
  const [query, setQuery] = useState("");

  const siteNames = useMemo(
    () => ["전체", ...Array.from(new Set(rows.map((row) => row.siteName))).sort()],
    [rows],
  );

  const filteredRows = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return rows
      .filter((row) => siteFilter === "전체" || row.siteName === siteFilter)
      .filter((row) => productFilter === "전체" || row.productType === productFilter)
      .filter((row) => {
        if (!keyword) return true;
        return [
          row.siteName,
          row.carrierName,
          row.internetName,
          row.tvName,
          row.baseFee,
          row.giftAmount,
        ]
          .join(" ")
          .toLowerCase()
          .includes(keyword);
      })
      .sort((a, b) => b.giftAmountWon - a.giftAmountWon);
  }, [productFilter, query, rows, siteFilter]);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-4 border-b border-slate-100 p-6 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-sm font-bold text-blue-600">Latest Sheet Rows</p>
          <h2 className="text-xl font-black text-slate-950">최신 크롤링 데이터 테이블</h2>
          <p className="mt-1 text-sm text-slate-500">
            사이트, 상품 유형, 키워드로 빠르게 확인할 수 있습니다.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <select
            value={siteFilter}
            onChange={(event) => setSiteFilter(event.target.value)}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:border-blue-400"
          >
            {siteNames.map((siteName) => (
              <option key={siteName} value={siteName}>
                {siteName}
              </option>
            ))}
          </select>
          <select
            value={productFilter}
            onChange={(event) => setProductFilter(event.target.value)}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:border-blue-400"
          >
            <option value="전체">전체 상품</option>
            <option value="인터넷+TV">인터넷+TV</option>
            <option value="인터넷 단독">인터넷 단독</option>
          </select>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="상품명/통신사 검색"
            className="min-w-[220px] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-400"
          />
        </div>
      </div>
      <div className="max-h-[520px] overflow-auto">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-4">수집 일시</th>
              <th className="px-5 py-4">사이트</th>
              <th className="px-5 py-4">통신사</th>
              <th className="px-5 py-4">유형</th>
              <th className="px-5 py-4">인터넷 상품</th>
              <th className="px-5 py-4">TV 상품</th>
              <th className="px-5 py-4 text-right">기본 요금</th>
              <th className="px-5 py-4 text-right">사은품</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredRows.map((row, index) => (
              <tr key={`${row.collectedAt}-${row.siteName}-${index}`} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-5 py-4 text-slate-600">{row.collectedAt}</td>
                <td className="px-5 py-4 font-semibold text-slate-950">{row.siteName}</td>
                <td className="px-5 py-4 text-slate-700">{row.carrierName}</td>
                <td className="px-5 py-4">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                    {row.productType}
                  </span>
                </td>
                <td className="max-w-[260px] px-5 py-4 text-slate-700">{row.internetName}</td>
                <td className="max-w-[220px] px-5 py-4 text-slate-700">{row.tvName || "-"}</td>
                <td className="whitespace-nowrap px-5 py-4 text-right font-semibold text-slate-950">
                  {row.baseFee || "-"}
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-right font-semibold text-emerald-700">
                  {row.giftAmount || "-"}
                </td>
              </tr>
            ))}
            {!filteredRows.length ? (
              <tr>
                <td colSpan={8} className="px-5 py-12 text-center text-slate-500">
                  조건에 맞는 데이터가 없습니다.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className="border-t border-slate-100 px-6 py-4 text-sm text-slate-500">
        표시 {filteredRows.length.toLocaleString("ko-KR")}건 / 최신 데이터{" "}
        {rows.length.toLocaleString("ko-KR")}건
      </div>
    </div>
  );
}
