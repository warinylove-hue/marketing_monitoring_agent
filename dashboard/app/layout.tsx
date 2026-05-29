import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "대표 통신판매 사이트 상품 요금 및 사은품 대시 보드",
  description: "Google Sheet 크롤링 데이터를 시각화하고 AI가 최신 데이터를 분석하는 대시보드",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
