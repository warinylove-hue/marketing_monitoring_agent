import { readMarketingSheets } from "@/lib/googleSheets";
import { formatWon, parseKoreanMoney } from "@/lib/money";
import type {
  CrawlRow,
  DashboardData,
  DashboardKpis,
  SiteSummary,
  TopGiftItem,
  TrendPoint,
} from "@/types/dashboard";

const SITE_NAMES = ["아정당", "MISO", "U+", "KT", "SKB", "SKT"];

export async function getDashboardData(): Promise<DashboardData> {
  const rawRows = await readMarketingSheets();
  const rows: CrawlRow[] = rawRows
    .map(({ sheetName, values }) => {
      const [
        collectedAt = "",
        rawSiteName = "",
        carrierName = "",
        internetName = "",
        tvName = "",
        baseFee = "",
        giftAmount = "",
      ] = values;

      const productType: CrawlRow["productType"] = tvName ? "인터넷+TV" : "인터넷 단독";
      const siteName = normalizeSiteName(rawSiteName, sheetName);

      return {
        collectedAt,
        date: collectedAt.slice(0, 10),
        siteName,
        carrierName,
        internetName,
        tvName,
        productType,
        baseFee,
        giftAmount,
        baseFeeWon: parseKoreanMoney(baseFee),
        giftAmountWon: parseKoreanMoney(giftAmount),
      };
    })
    .filter((row) => row.collectedAt && row.siteName);

  const latestDate = rows
    .map((row) => row.date)
    .sort()
    .at(-1) || "";
  const latestRows = rows.filter((row) => row.date === latestDate);
  const topGiftRows = buildTopGiftRows(latestRows);

  return {
    generatedAt: new Date().toISOString(),
    latestDate,
    kpis: buildKpis(rows, latestRows, topGiftRows),
    rows,
    latestRows,
    trend: buildGiftTrend(rows),
    siteSummaries: buildSiteSummaries(rows, latestRows),
    topGiftRows,
    aiSummary: buildAiSummary(rows, latestRows, latestDate, topGiftRows),
  };
}

function buildGiftTrend(rows: CrawlRow[]): TrendPoint[] {
  const byDate = new Map<string, TrendPoint>();

  for (const row of rows) {
    if (!row.date || !row.siteName) continue;
    const point = byDate.get(row.date) || { date: row.date };
    const current = Number(point[row.siteName] || 0);
    point[row.siteName] = Math.max(current, row.giftAmountWon);
    byDate.set(row.date, point);
  }

  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

function buildSiteSummaries(rows: CrawlRow[], latestRows: CrawlRow[]): SiteSummary[] {
  return SITE_NAMES.map((siteName) => {
    const allSiteRows = rows.filter((row) => row.siteName === siteName);
    const latestSiteRows = latestRows.filter((row) => row.siteName === siteName);
    const giftRows = latestSiteRows.filter((row) => row.giftAmountWon > 0);
    const giftSum = giftRows.reduce((sum, row) => sum + row.giftAmountWon, 0);
    const baseFeeRows = latestSiteRows.filter((row) => row.baseFeeWon > 0);
    const baseFeeSum = baseFeeRows.reduce((sum, row) => sum + row.baseFeeWon, 0);
    const bestRow = [...latestSiteRows].sort((a, b) => b.giftAmountWon - a.giftAmountWon)[0];

    return {
      siteName,
      rowCount: allSiteRows.length,
      latestRowCount: latestSiteRows.length,
      maxGiftWon: Math.max(0, ...latestSiteRows.map((row) => row.giftAmountWon)),
      averageGiftWon: giftRows.length ? giftSum / giftRows.length : 0,
      averageBaseFeeWon: baseFeeRows.length ? baseFeeSum / baseFeeRows.length : 0,
      bestProductLabel: bestRow ? productLabel(bestRow) : "-",
    };
  });
}

function buildTopGiftRows(latestRows: CrawlRow[]): TopGiftItem[] {
  return [...latestRows]
    .filter((row) => row.giftAmountWon > 0)
    .sort((a, b) => b.giftAmountWon - a.giftAmountWon)
    .slice(0, 20)
    .map((row, index) => ({
      rank: index + 1,
      siteName: row.siteName,
      carrierName: row.carrierName,
      productLabel: productLabel(row),
      baseFee: row.baseFee,
      giftAmount: row.giftAmount,
      giftAmountWon: row.giftAmountWon,
    }));
}

function buildKpis(
  rows: CrawlRow[],
  latestRows: CrawlRow[],
  topGiftRows: TopGiftItem[],
): DashboardKpis {
  const giftRows = latestRows.filter((row) => row.giftAmountWon > 0);
  const giftSum = giftRows.reduce((sum, row) => sum + row.giftAmountWon, 0);
  const best = topGiftRows[0];

  return {
    totalRows: rows.length,
    latestRowCount: latestRows.length,
    activeSiteCount: new Set(latestRows.map((row) => row.siteName)).size,
    maxGiftWon: best?.giftAmountWon || 0,
    maxGiftSite: best?.siteName || "",
    maxGiftProduct: best?.productLabel || "",
    averageGiftWon: giftRows.length ? giftSum / giftRows.length : 0,
  };
}

function buildAiSummary(
  rows: CrawlRow[],
  latestRows: CrawlRow[],
  latestDate: string,
  topGiftRows: TopGiftItem[],
) {
  const topGiftText = topGiftRows
    .slice(0, 15)
    .map(
      (row) =>
        `${row.rank}. ${row.siteName}/${row.carrierName} | ${row.productLabel} | 요금 ${row.baseFee} | 사은품 ${row.giftAmount}`,
    );

  const counts = SITE_NAMES.map((siteName) => {
    const count = latestRows.filter((row) => row.siteName === siteName).length;
    return `${siteName}: ${count}건`;
  }).join(", ");

  const siteSummaryText = buildSiteSummaries(rows, latestRows)
    .map(
      (site) =>
        `${site.siteName}: 최신 ${site.latestRowCount}건, 최고 ${formatWon(
          site.maxGiftWon,
        )}, 평균 사은품 ${formatWon(site.averageGiftWon)}, 대표 상품 ${site.bestProductLabel}`,
    )
    .join("\n");
  const dailySummaryText = buildDailyComparisonSummary(rows);

  return [
    `최신 수집일: ${latestDate || "없음"}`,
    `전체 누적 행 수: ${rows.length}건`,
    `최신 수집 건수: ${counts}`,
    "",
    "[사이트별 최신 요약]",
    siteSummaryText || "사이트별 요약 없음",
    "",
    `최신 데이터 중 최고 사은품: ${
      topGiftText[0] || "사은품 데이터 없음"
    }`,
    `최신 상위 사은품 목록:\n${topGiftText.join("\n")}`,
    "",
    "[날짜별 비교 요약]",
    dailySummaryText || "날짜별 비교 데이터 없음",
    `사은품 금액은 내부적으로 원 단위로도 변환되어 있으며, 예: ${formatWon(
      latestRows[0]?.giftAmountWon || 0,
    )}`,
  ].join("\n");
}

function buildDailyComparisonSummary(rows: CrawlRow[]): string {
  const dates = Array.from(new Set(rows.map((row) => row.date).filter(Boolean)))
    .sort((a, b) => b.localeCompare(a))
    .slice(0, 30);

  return dates
    .map((date) => {
      const dateRows = rows.filter((row) => row.date === date);
      const giftRows = dateRows.filter((row) => row.giftAmountWon > 0);
      const giftSum = giftRows.reduce((sum, row) => sum + row.giftAmountWon, 0);
      const bestRow = [...giftRows].sort((a, b) => b.giftAmountWon - a.giftAmountWon)[0];
      const siteMaxText = SITE_NAMES.map((siteName) => {
        const siteBest = dateRows
          .filter((row) => row.siteName === siteName)
          .sort((a, b) => b.giftAmountWon - a.giftAmountWon)[0];
        return `${siteName} ${siteBest ? formatWon(siteBest.giftAmountWon) : "없음"}`;
      }).join(", ");

      return [
        `${date}: 총 ${dateRows.length}건, 평균 사은품 ${formatWon(
          giftRows.length ? giftSum / giftRows.length : 0,
        )}`,
        `최고 ${bestRow ? `${bestRow.siteName}/${bestRow.carrierName} ${productLabel(bestRow)} ${bestRow.giftAmount}` : "없음"}`,
        `사이트별 최고: ${siteMaxText}`,
      ].join(" | ");
    })
    .join("\n");
}

function productLabel(row: CrawlRow): string {
  return [row.internetName, row.tvName || "인터넷 단독"].filter(Boolean).join(" / ");
}

function normalizeSiteName(rawSiteName: string, sheetName: string): string {
  if (sheetName === "아정당" || rawSiteName.includes("아정당")) return "아정당";
  if (sheetName === "U+" || rawSiteName === "LGu+") return "U+";
  return sheetName || rawSiteName;
}
