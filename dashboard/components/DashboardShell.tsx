"use client";

import { useEffect, useMemo, useState } from "react";
import { Play, RefreshCw } from "lucide-react";

import { ChatPanel } from "@/components/ChatPanel";
import { DataTable } from "@/components/DataTable";
import { GiftTrendChart } from "@/components/GiftTrendChart";
import { SummaryCards } from "@/components/SummaryCards";
import { TopGiftRanking } from "@/components/TopGiftRanking";
import type { DashboardData } from "@/types/dashboard";

export function DashboardShell() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isStartingCrawl, setIsStartingCrawl] = useState(false);
  const [crawlMessage, setCrawlMessage] = useState("");

  async function loadDashboard() {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch("/api/dashboard", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "대시보드 데이터를 불러오지 못했습니다.");
      }
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function startManualCrawl() {
    setIsStartingCrawl(true);
    setCrawlMessage("");
    setError("");
    try {
      const response = await fetch("/api/crawl", {
        method: "POST",
        cache: "no-store",
      });
      const payload = await response.json();
      if (response.status === 501 && payload.message) {
        setCrawlMessage(payload.message);
        return;
      }
      if (!response.ok) {
        throw new Error(payload.error || "자료 수집을 시작하지 못했습니다.");
      }
      setCrawlMessage(
        payload.message ||
          "자료 수집을 시작했습니다. 완료되면 Google Sheet에 저장되고, 이후 '최신 저장된 정보 불러오기'를 눌러 화면에 반영하세요.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "자료 수집 실행 중 오류가 발생했습니다.");
    } finally {
      setIsStartingCrawl(false);
    }
  }

  const latestRows = useMemo(() => data?.latestRows || [], [data]);
  const latestCollectedAt = useMemo(
    () => latestRows.map((row) => row.collectedAt).sort().at(-1) || "-",
    [latestRows],
  );
  const latestLoadedAt = data?.generatedAt ? formatDateTime(data.generatedAt) : "-";

  return (
    <main className="grid min-h-screen gap-6 p-4 md:p-6 lg:grid-cols-[minmax(0,1fr)_390px] 2xl:grid-cols-[minmax(0,1fr)_430px]">
      <section className="space-y-6">
        <header className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white/85 p-8 shadow-sm backdrop-blur">
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.22em] text-blue-600">
                Marketing Intelligence Center
              </p>
              <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
                대표 통신판매 사이트 상품 요금 및 사은품 대시 보드
              </h1>
              <p className="mt-3 max-w-3xl text-slate-600">
                Google Sheet에 누적된 6개 사이트 크롤링 데이터를 기준으로 사은품 변동,
                사이트별 경쟁력, 상품 조합별 우위를 한 화면에서 확인합니다.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto">
              <p className="text-right text-xs font-black text-blue-700">
                최신 수집 일시 <span className="ml-1 text-slate-600">{latestCollectedAt}</span>
              </p>
              <button
                type="button"
                onClick={() => void startManualCrawl()}
                disabled={isStartingCrawl}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-black text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Play size={16} />
                지금 자료 수집하기
              </button>
              <p className="mt-2 text-right text-xs font-black text-slate-700">
                최신 저장 일시 <span className="ml-1 text-slate-600">{latestLoadedAt}</span>
              </p>
              <button
                type="button"
                onClick={() => void loadDashboard()}
                disabled={isLoading}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
                최신 저장된 정보 불러오기
              </button>
            </div>
          </div>
          {crawlMessage ? (
            <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-800">
              {crawlMessage}
            </div>
          ) : null}
          <div className="mt-6 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="font-black text-slate-950">좌측 대시보드</p>
              <p className="mt-1">사은품 추이 차트와 최신 데이터 테이블</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="font-black text-slate-950">우측 AI 채팅창</p>
              <p className="mt-1">시트 최신 요약을 기반으로 실시간 답변</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="font-black text-slate-950">데이터 출처</p>
              <p className="mt-1">마케팅_크롤링_DB Google Sheet</p>
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700">
            {error}
          </div>
        ) : null}

        {data ? (
          <>
            <SummaryCards latestDate={data.latestDate} kpis={data.kpis} summaries={data.siteSummaries} />
            <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
              <GiftTrendChart data={data.trend} />
              <TopGiftRanking items={data.topGiftRows} />
            </div>
            <DataTable rows={latestRows} />
          </>
        ) : (
          <div className="rounded-3xl border border-slate-200 bg-white p-10 text-slate-500">
            {isLoading ? "Google Sheet 데이터를 불러오는 중입니다..." : "표시할 데이터가 없습니다."}
          </div>
        )}
      </section>

      <ChatPanel />
    </main>
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}
