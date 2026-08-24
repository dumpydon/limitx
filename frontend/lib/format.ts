export function price(ticks: number | null | undefined): string {
  if (ticks === null || ticks === undefined) return "—";
  return (ticks / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function integer(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Math.round(value).toLocaleString("en-US");
}

export function compact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function latency(ns: number | null | undefined): string {
  if (ns === null || ns === undefined) return "Not measured";
  return ns < 1_000 ? `${integer(ns)} ns` : `${(ns / 1_000).toFixed(1)} μs`;
}

export function decimalToTicks(value: string): number | null {
  const normalized = value.trim().replaceAll(",", "");
  if (!/^\d+(\.\d{0,2})?$/.test(normalized)) return null;
  const [whole, fraction = ""] = normalized.split(".");
  return Number.parseInt(whole, 10) * 100 + Number.parseInt(fraction.padEnd(2, "0") || "0", 10);
}

