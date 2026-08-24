import { price } from "@/lib/format";
import type { Level } from "@/types/market";
import { Panel } from "./Panel";

function points(levels: Level[], width: number, height: number, reverse = false): string {
  if (!levels.length) return "";
  let cumulative = 0;
  const totals = levels.map((level) => (cumulative += level.quantity));
  const max = Math.max(...totals, 1);
  const source = reverse ? [...totals].reverse() : totals;
  return source.map((total, index) => `${(index / Math.max(source.length - 1, 1)) * width},${height - (total / max) * (height - 20)}`).join(" ");
}

export function DepthChart({ bids, asks }: { bids: Level[]; asks: Level[] }) {
  const bidPoints = points(bids.slice(0, 14), 300, 180, true);
  const askPoints = points(asks.slice(0, 14), 300, 180);
  return (
    <Panel title="Cumulative Depth" eyebrow="LIQUIDITY PROFILE" className="depth-panel" action={<span className="live-mark">● LIVE</span>}>
      <div className="chart-wrap">
        <svg viewBox="0 0 640 220" role="img" aria-label="Cumulative bid and ask depth chart">
          <defs>
            <linearGradient id="bid-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#39d5a1" stopOpacity=".32" /><stop offset="1" stopColor="#39d5a1" stopOpacity="0" /></linearGradient>
            <linearGradient id="ask-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff6c7d" stopOpacity=".3" /><stop offset="1" stopColor="#ff6c7d" stopOpacity="0" /></linearGradient>
          </defs>
          {[30, 80, 130, 180].map((y) => <line key={y} x1="0" y1={y} x2="640" y2={y} className="grid-line" />)}
          {bidPoints ? <><polyline points={bidPoints} transform="translate(0 10)" className="bid-line" /><polygon points={`0,210 ${bidPoints} 300,210`} fill="url(#bid-area)" /></> : null}
          {askPoints ? <><polyline points={askPoints} transform="translate(340 10)" className="ask-line" /><polygon points={`340,210 ${askPoints.split(" ").map((p) => { const [x,y] = p.split(","); return `${Number(x)+340},${Number(y)+10}`; }).join(" ")} 640,210`} fill="url(#ask-area)" /></> : null}
          <line x1="320" y1="8" x2="320" y2="210" className="mid-line" />
        </svg>
        <div className="chart-axis"><span>{price(bids.at(-1)?.price_ticks)}</span><strong>MID</strong><span>{price(asks.at(-1)?.price_ticks)}</span></div>
      </div>
    </Panel>
  );
}

