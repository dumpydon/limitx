import type { LogoPulse, LogoPulseState } from "@/types/logo";

const LABELS: Record<LogoPulse, string> = {
  idle: "Idle",
  buy: "Buy order accepted",
  sell: "Sell order accepted",
  trade: "Trade executed",
  sweep: "Multi-level sweep executed",
  reject: "Order rejected",
  resync: "Market data resynchronized",
};

export function LogoMark({
  pulse,
  preview,
}: {
  pulse: LogoPulseState;
  preview: "buy" | "sell" | null;
}) {
  return (
    <div
      className="limitx-mark"
      data-pulse={pulse.type}
      data-pulse-id={pulse.id}
      data-preview={preview ?? "none"}
      aria-label={`Limit X. ${LABELS[pulse.type]}`}
      title={LABELS[pulse.type]}
    >
      <span className="limit-word">LIMIT</span>
      <span className="limit-divider">/</span>
      <span className="x-anchor" aria-hidden="true">
        <svg viewBox="0 0 38 38" focusable="false">
          <path className="x-rail x-rail-buy" d="M6 5.5 32 32.5" />
          <path className="x-rail x-rail-sell" d="M32 5.5 6 32.5" />
          <path className="x-core" d="m19 14 5 5-5 5-5-5Z" />
          <path className="x-tick x-tick-top" d="M19 3v5" />
          <path className="x-tick x-tick-bottom" d="M19 30v5" />
        </svg>
        <i className="x-scan" />
      </span>
    </div>
  );
}

