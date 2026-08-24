export type Side = "BUY" | "SELL";

export interface Level {
  price_ticks: number;
  quantity: number;
  order_count: number;
}

export interface L1 {
  best_bid: number | null;
  best_ask: number | null;
  spread_ticks: number | null;
  mid_ticks_x2: number | null;
}

export interface Trade {
  sequence: number;
  logical_time_ns: number;
  price_ticks: number;
  quantity: number;
  aggressor_side: Side;
  maker_order_id: string;
  taker_order_id: string;
}

export interface MarketPayload {
  l1: L1;
  depth: { bids: Level[]; asks: Level[] };
  recent_trades?: Trade[];
  volume?: number;
  vwap_ticks?: number | null;
  checksum: string;
  previous_sequence?: number;
}

export interface Envelope {
  type: "book_snapshot" | "book_delta" | "trade";
  sequence: number;
  symbol: string;
  payload: MarketPayload | Trade;
}

export interface LiveOrder {
  order_id: string;
  symbol: string;
  account_id: string;
  side: Side;
  order_type: string;
  time_in_force: string;
  price_ticks: number | null;
  quantity: number;
  remaining_qty: number;
  filled_qty: number;
  status: string;
  accepted_sequence: number;
}

export type SyncStatus = "CONNECTING" | "LIVE" | "RESYNCING" | "OFFLINE";

