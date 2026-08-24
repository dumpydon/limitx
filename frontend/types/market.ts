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
  trade_id?: string;
  slippage_ticks_x2?: number | null;
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

export type FailureMode = "none" | "drop" | "duplicate" | "delay" | "out_of_order";

export interface SyncEvent {
  id: number;
  state: "INFO" | "FAULT" | "GAP" | "RECOVERY" | "RECOVERED";
  detail: string;
  expected?: number;
  received?: number;
}

export interface SystemState {
  engine_sequence: number;
  active_orders: number;
  bid_levels: number;
  ask_levels: number;
  event_journal_size: number;
  connected_clients: number;
  queue_depth: number;
  snapshot_sequence: number;
  last_checksum: string;
  snapshot_size_bytes: number;
  process_max_rss_platform_units: number;
  reference_price_ticks: number;
  last_trade_ticks: number | null;
  absolute_move_ticks: number;
  percentage_move: number;
  instrument: {
    display_name: string;
    tick_size: string;
    quantity_unit: string;
    provenance: string;
  };
  metrics: Record<string, number | null>;
}

export interface MarketSummary {
  symbol: string;
  best_bid: number | null;
  best_ask: number | null;
  spread_ticks: number | null;
  last_trade_ticks: number | null;
  volume: number;
  sequence: number;
  worker_queue_depth: number;
  status: string;
  scenario: string | null;
}

export interface Lifecycle {
  order_id: string;
  symbol: string;
  status: string;
  requested_quantity: number;
  filled_quantity: number;
  remaining_quantity: number;
  explanation: string;
  timeline: Array<{
    sequence: number;
    evidence_id: string;
    type: string;
    stage: string;
    facts: Record<string, unknown>;
  }>;
  pipeline: Array<{ stage: string; evidence_id: string; basis: string }>;
  execution: {
    trade_count: number;
    levels_consumed: number[];
    vwap_ticks: number | null;
    trades: Array<Record<string, unknown>>;
  };
}
