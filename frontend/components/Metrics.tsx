import { integer, price } from "@/lib/format";
import { Panel } from "./Panel";

export function Metrics({ data }: { data: Record<string, number | null> }) {
  const items = [
    ["Spread", data.spread_ticks == null ? "—" : `${data.spread_ticks} ticks`, "Best ask minus best bid."],
    ["Mid price", price(data.mid_ticks), "Arithmetic midpoint of best bid and best ask."],
    ["VWAP", price(data.vwap_ticks), "Quantity-weighted price across session executions."],
    ["Trade volume", integer(data.trade_volume), "Total matched quantity in this session."],
    ["Depth imbalance", data.depth_imbalance == null ? "—" : `${(data.depth_imbalance * 100).toFixed(1)}%`, "(Bid depth − ask depth) / total visible depth."],
    ["Flow imbalance", data.order_flow_imbalance == null ? "—" : `${(data.order_flow_imbalance * 100).toFixed(1)}%`, "Buy minus sell aggressor volume, normalized by total volume."],
    ["Cancel / add", data.cancel_to_add_ratio == null ? "—" : data.cancel_to_add_ratio.toFixed(2), "Cancellation events divided by accepted orders."],
    ["Fill ratio", data.fill_ratio == null ? "—" : `${(data.fill_ratio * 100).toFixed(1)}%`, "Filled order events divided by accepted orders."],
    ["Avg slippage", data.average_aggressive_slippage_ticks == null ? "—" : `${data.average_aggressive_slippage_ticks.toFixed(2)} ticks`, "Signed execution distance from arrival midpoint."],
  ];
  return (
    <Panel title="Market structure" eyebrow="Session analytics">
      <div className="metric-grid">{items.map(([label, value, definition]) => <div className="metric-cell" key={label} title={definition}><span>{label} <i>ⓘ</i></span><strong>{value}</strong></div>)}</div>
      <div className="imbalance-bar"><span style={{ width: `${50 + Math.max(-50, Math.min(50, (data.depth_imbalance ?? 0) * 50))}%` }} /><i /></div>
      <div className="imbalance-label"><span>Bid depth</span><span>Ask depth</span></div>
    </Panel>
  );
}
