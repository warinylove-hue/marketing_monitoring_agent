export function parseKoreanMoney(value: string): number {
  const normalized = value.replace(/\s/g, "");
  if (!normalized) return 0;

  const numberText = normalized.replace(/[^\d,.-]/g, "").replace(/,/g, "");
  const amount = Number(numberText);
  if (!Number.isFinite(amount)) return 0;

  if (normalized.includes("만원")) return amount * 10_000;
  return amount;
}

export function formatWon(value: number): string {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}
