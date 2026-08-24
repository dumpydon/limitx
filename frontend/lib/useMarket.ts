"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, websocketUrl } from "./api";
import type { Envelope, MarketPayload, SyncStatus, Trade } from "@/types/market";

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
  const [failureMode, setFailureMode] = useState<"none" | "drop" | "duplicate" | "delay">("none");
  const lastDepthSequence = useRef(0);
  const injected = useRef(false);

  const applySnapshot = useCallback((envelope: Envelope) => {
    const payload = envelope.payload as MarketPayload;
    setMarket(payload);
    setTrades(payload.recent_trades ?? []);
    setSequence(envelope.sequence);
    lastDepthSequence.current = envelope.sequence;
    setStatus("LIVE");
  }, []);

  const resync = useCallback(async () => {
    setStatus("RESYNCING");
    const snapshot = await api<Envelope>(`/api/book/${symbol}`);
    applySnapshot(snapshot);
  }, [applySnapshot, symbol]);

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
          setTrades((current) => [trade, ...current].slice(0, 80));
          return;
        }
        const payload = envelope.payload as MarketPayload;
        if (!injected.current && failureMode !== "none") {
          injected.current = true;
          if (failureMode === "drop") return;
          if (failureMode === "delay") {
            window.setTimeout(() => void resync(), 250);
            return;
          }
          if (failureMode === "duplicate") {
            void resync();
            return;
          }
        }
        if (payload.previous_sequence !== lastDepthSequence.current) {
          void resync();
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
  }, [applySnapshot, failureMode, resync, symbol]);

  return { market, trades, sequence, status, failureMode, setFailureMode, resync };
}
