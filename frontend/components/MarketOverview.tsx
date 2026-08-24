import { integer, price } from "@/lib/format";
import type { MarketSummary } from "@/types/market";

const INSTRUMENT_NAMES: Record<string, string> = {
  "BTC-USD": "Bitcoin",
  "ETH-USD": "Ethereum",
  AAPL: "Apple",
  MSFT: "Microsoft",
};

export function MarketOverview({
  markets,
  selected,
  onSelect,
}: {
  markets: MarketSummary[];
  selected: string;
  onSelect: (symbol: string) => void;
}) {
  return <section className="market-overview" aria-label="Independent symbol engines">{markets.map((market) => <button key={market.symbol} className={selected === market.symbol ? "active" : ""} onClick={() => onSelect(market.symbol)}><header><div className="symbol-name"><strong>{market.symbol}</strong><small>({INSTRUMENT_NAMES[market.symbol] ?? "Simulated instrument"})</small></div><span><i />{market.status}</span></header><div><b>{price(market.last_trade_ticks ?? (market.best_bid && market.best_ask ? (market.best_bid + market.best_ask) / 2 : null))}</b><small>VOL {integer(market.volume)}</small></div><footer><span>{price(market.best_bid)} / {price(market.best_ask)}</span><code>SEQ {integer(market.sequence)}</code></footer></button>)}</section>;
}
