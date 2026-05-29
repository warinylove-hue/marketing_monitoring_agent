export type CrawlRow = {
  collectedAt: string;
  date: string;
  siteName: string;
  carrierName: string;
  internetName: string;
  tvName: string;
  productType: "인터넷+TV" | "인터넷 단독";
  baseFee: string;
  giftAmount: string;
  baseFeeWon: number;
  giftAmountWon: number;
};

export type TrendPoint = {
  date: string;
  [siteName: string]: string | number;
};

export type SiteSummary = {
  siteName: string;
  rowCount: number;
  latestRowCount: number;
  maxGiftWon: number;
  averageGiftWon: number;
  averageBaseFeeWon: number;
  bestProductLabel: string;
};

export type DashboardKpis = {
  totalRows: number;
  latestRowCount: number;
  activeSiteCount: number;
  maxGiftWon: number;
  maxGiftSite: string;
  maxGiftProduct: string;
  averageGiftWon: number;
};

export type TopGiftItem = {
  rank: number;
  siteName: string;
  carrierName: string;
  productLabel: string;
  baseFee: string;
  giftAmount: string;
  giftAmountWon: number;
};

export type DashboardData = {
  generatedAt: string;
  latestDate: string;
  kpis: DashboardKpis;
  rows: CrawlRow[];
  latestRows: CrawlRow[];
  trend: TrendPoint[];
  siteSummaries: SiteSummary[];
  topGiftRows: TopGiftItem[];
  aiSummary: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};
