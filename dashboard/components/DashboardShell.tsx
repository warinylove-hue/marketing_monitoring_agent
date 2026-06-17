"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Play, RefreshCw } from "lucide-react";

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
  const [isCrawlConfirmOpen, setIsCrawlConfirmOpen] = useState(false);

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
    setIsCrawlConfirmOpen(false);
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
  const latestCollectedAt = data?.latestCollectedAt || "-";
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
                매일 오전 8시에 자동으로 대표 통신 6개 사이트를 크롤링하여 통신사별,
                상품별 제안 요금 및 사은품 정보를 업데이트 합니다.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto">
              <p className="text-right text-xs font-black text-blue-700">
                최신 수집 일시 <span className="ml-1 text-slate-600">{latestCollectedAt}</span>
              </p>
              <button
                type="button"
                onClick={() => setIsCrawlConfirmOpen(true)}
                disabled={isStartingCrawl}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-amber-600 px-5 py-3 text-sm font-black text-white transition hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Play size={16} />
                관리자용 수동 크롤링 실행
              </button>
              <p className="text-right text-xs leading-5 text-amber-700">
                누르면 6개 사이트를 다시 수집하고 Google Sheet에 새 데이터가 추가됩니다.
              </p>
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
      {isCrawlConfirmOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
          <div className="w-full max-w-lg rounded-[2rem] bg-white p-6 shadow-2xl">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
                <AlertTriangle size={24} />
              </div>
              <div>
                <p className="text-sm font-black text-amber-700">관리자 확인 필요</p>
                <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">
                  지금 새 크롤링을 실행할까요?
                </h2>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  이 작업은 6개 사이트를 다시 방문해 약 40분간 데이터를 수집하고,
                  Google Sheet에 새 행을 추가합니다. 단순 화면 갱신은 아래의
                  "최신 저장된 정보 불러오기" 버튼을 사용하세요.
                </p>
              </div>
            </div>
            <div className="mt-6 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-bold text-slate-950">실행 결과</p>
              <p className="mt-1">새 수집 묶음이 생성되며, 중복 실행 시 같은 날짜 데이터가 여러 번 쌓일 수 있습니다.</p>
            </div>
            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setIsCrawlConfirmOpen(false)}
                className="rounded-2xl border border-slate-200 px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => void startManualCrawl()}
                disabled={isStartingCrawl}
                className="rounded-2xl bg-amber-600 px-5 py-3 text-sm font-black text-white transition hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                네, 지금 크롤링 실행
              </button>
            </div>
          </div>
        </div>
      ) : null}
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
