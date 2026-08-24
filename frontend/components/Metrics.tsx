import { integer, price } from "@/lib/format";
import { Panel } from "./Panel";

export function Metrics({ data }: { data: Record<string, number | null> }) {
  const items = [
    ["Mid price", price(data.mid_ticks)],
    ["VWAP", price(data.vwap_ticks)],
    ["Trade volume", integer(data.trade_volume)],
    ["Depth imbalance", data.depth_imbalance == null ? "—" : `${(data.depth_imbalance * 100).toFixed(1)}%`],
    ["Order-flow imbalance", data.order_flow_imbalance == null ? "—" : `${(data.order_flow_imbalance * 100).toFixed(1)}%`],
    ["Cancel / add", data.cancel_to_add_ratio == null ? "—" : data.cancel_to_add_ratio.toFixed(2)],
  ];
  return (
    <Panel title="Microstructure" eyebrow="DETERMINISTIC ANALYTICS">
      <div className="metric-grid">{items.map(([label, value]) => <div className="metric-cell" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      <div className="imbalance-bar"><span style={{ width: `${50 + Math.max(-50, Math.min(50, (data.depth_imbalance ?? 0) * 50))}%` }} /><i /></div>
      <div className="imbalance-label"><span>BID DEPTH</span><span>ASK DEPTH</span></div>
    </Panel>
  );
}

