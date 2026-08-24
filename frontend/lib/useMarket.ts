"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, websocketUrl } from "./api";
import type {
  Envelope,
  FailureMode,
  MarketPayload,
  SyncEvent,
  SyncStatus,
  Trade,
} from "@/types/market";
import type { LogoPulseState } from "@/types/logo";

const EMPTY: MarketPayload = {
  l1: { best_bid: null, best_ask: null, spread_ticks: null, mid_ticks_x2: null },
  depth: { bids: [], asks: [] },
  recent_trades: [],
  checksum: "—",
};

export function useMarket(symbol: string) {
  const [market, setMarket] = useState<MarketPayload>(EMPTY);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [sequence, setSequence] = useState(0);
  const [status, setStatus] = useState<SyncStatus>("CONNECTING");
  const [failureMode, setFailureModeState] = useState<FailureMode>("none");
  const [syncEvents, setSyncEvents] = useState<SyncEvent[]>([]);
  const [enginePulse, setEnginePulse] = useState<LogoPulseState | null>(null);
  const lastDepthSequence = useRef(0);
  const injected = useRef(false);
  const failureModeRef = useRef<FailureMode>("none");
  const syncEventId = useRef(0);
  const resyncingRef = useRef(false);
  const sweepGroup = useRef<{ taker: string; prices: Set<number> }>({ taker: "", prices: new Set() });

  const logSync = useCallback(
    (event: Omit<SyncEvent, "id">) => {
      syncEventId.current += 1;
      setSyncEvents((current) => [...current, { id: syncEventId.current, ...event }].slice(-12));
    },
    [],
  );

  const setFailureMode = useCallback((mode: FailureMode) => {
    failureModeRef.current = mode;
    injected.current = false;
    setFailureModeState(mode);
  }, []);

  const applySnapshot = useCallback((envelope: Envelope, recovery = false) => {
    const payload = envelope.payload as MarketPayload;
    setMarket(payload);
    setTrades(payload.recent_trades ?? []);
    setSequence(envelope.sequence);
    lastDepthSequence.current = envelope.sequence;
    setStatus("LIVE");
    if (recovery) {
      setEnginePulse({ type: "resync", id: envelope.sequence });
      logSync({
        state: "RECOVERED",
        detail: `Snapshot ${envelope.sequence.toLocaleString()} applied; client recovered`,
        received: envelope.sequence,
      });
    }
  }, [logSync]);

  const resync = useCallback(async (expected?: number, received?: number) => {
    if (resyncingRef.current) return;
    resyncingRef.current = true;
    setStatus("RESYNCING");
    logSync({
      state: "RECOVERY",
      detail: "Resynchronizing from authoritative L2 snapshot",
      expected,
      received,
    });
    try {
      const snapshot = await api<Envelope>(`/api/book/${symbol}`);
      applySnapshot(snapshot, true);
    } finally {
      resyncingRef.current = false;
    }
  }, [applySnapshot, logSync, symbol]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;
    injected.current = false;
    queueMicrotask(() => setStatus("CONNECTING"));

    const connect = () => {
      socket = new WebSocket(websocketUrl(`/ws/market/${symbol}`));
      socket.onmessage = (message) => {
        const envelope = JSON.parse(message.data as string) as Envelope;
        if (envelope.type === "book_snapshot") {
          applySnapshot(envelope);
          return;
        }
        if (envelope.type === "trade") {
          const trade = envelope.payload as Trade;
          if (sweepGroup.current.taker !== trade.taker_order_id) {
            sweepGroup.current = { taker: trade.taker_order_id, prices: new Set() };
          }
          sweepGroup.current.prices.add(trade.price_ticks);
          setEnginePulse({
            type: sweepGroup.current.prices.size >= 3 ? "sweep" : "trade",
            id: trade.sequence,
          });
          setTrades((current) => [trade, ...current].slice(0, 80));
          return;
        }
        const payload = envelope.payload as MarketPayload;
        const activeFault = failureModeRef.current;
        if (!injected.current && activeFault !== "none") {
          injected.current = true;
          if (activeFault === "drop") {
            logSync({
              state: "FAULT",
              detail: `Dropped delta ${envelope.sequence.toLocaleString()}; matcher state untouched`,
              received: envelope.sequence,
            });
            return;
          }
          if (activeFault === "delay") {
            logSync({
              state: "FAULT",
              detail: `Delayed delta ${envelope.sequence.toLocaleString()} at transport boundary`,
              received: envelope.sequence,
            });
            window.setTimeout(
              () => void resync(lastDepthSequence.current, envelope.sequence),
              300,
            );
            return;
          }
          if (activeFault === "out_of_order") {
            logSync({
              state: "GAP",
              detail: "Out-of-order delivery detected before projection mutation",
              expected: lastDepthSequence.current,
              received: envelope.sequence,
            });
            void resync(lastDepthSequence.current, envelope.sequence);
            return;
          }
          if (activeFault === "duplicate") {
            logSync({
              state: "FAULT",
              detail: `Duplicate delta ${envelope.sequence.toLocaleString()} ignored`,
              expected: lastDepthSequence.current,
              received: envelope.sequence,
            });
          }
        }
        if (payload.previous_sequence !== lastDepthSequence.current) {
          if (resyncingRef.current) return;
          logSync({
            state: "GAP",
            detail: "Client sequence gap detected; blind delta application stopped",
            expected: lastDepthSequence.current,
            received: payload.previous_sequence,
          });
          void resync(lastDepthSequence.current, payload.previous_sequence);
          return;
        }
        setMarket((current) => ({ ...current, ...payload }));
        setSequence(envelope.sequence);
        lastDepthSequence.current = envelope.sequence;
        setStatus("LIVE");
      };
      socket.onclose = () => {
        if (!disposed) {
          setStatus("OFFLINE");
          reconnect = setTimeout(connect, 1200);
        }
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => {
      disposed = true;
      if (reconnect) clearTimeout(reconnect);
      socket?.close();
    };
  }, [applySnapshot, logSync, resync, symbol]);

  return {
    market,
    trades,
    sequence,
    status,
    failureMode,
    setFailureMode,
    syncEvents,
    enginePulse,
    clearSyncEvents: () => setSyncEvents([]),
    resync,
  };
}
