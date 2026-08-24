"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LogoPulse, LogoPulseState } from "@/types/logo";

const PRIORITY: Record<LogoPulse, number> = {
  idle: 0,
  buy: 1,
  sell: 1,
  trade: 2,
  reject: 3,
  resync: 3,
  sweep: 4,
};

const DURATION: Record<LogoPulse, number> = {
  idle: 0,
  buy: 360,
  sell: 360,
  trade: 420,
  reject: 420,
  resync: 500,
  sweep: 520,
};

export function useLogoPulse() {
  const [pulse, setPulse] = useState<LogoPulseState>({ type: "idle", id: 0 });
  const active = useRef<LogoPulse>("idle");
  const pending = useRef<LogoPulse | null>(null);
  const nextId = useRef(0);
  const lastStartedAt = useRef(0);

  const trigger = useCallback((type: LogoPulse) => {
    if (type === "idle") return;
    const now = performance.now();
    const quietWindow = type === "trade" ? 900 : type === "sweep" ? 650 : 0;
    if (active.current === "idle" && now - lastStartedAt.current < quietWindow) return;
    if (active.current !== "idle") {
      if (PRIORITY[type] > PRIORITY[active.current]) {
        active.current = type;
        lastStartedAt.current = now;
        nextId.current += 1;
        setPulse({ type, id: nextId.current });
      } else if (type !== active.current && (!pending.current || PRIORITY[type] > PRIORITY[pending.current])) {
        pending.current = type;
      }
      return;
    }
    active.current = type;
    lastStartedAt.current = now;
    nextId.current += 1;
    setPulse({ type, id: nextId.current });
  }, []);

  useEffect(() => {
    if (pulse.type === "idle") return;
    const timer = window.setTimeout(() => {
      active.current = "idle";
      setPulse((current) => ({ type: "idle", id: current.id }));
      const queued = pending.current;
      pending.current = null;
      if (queued) window.setTimeout(() => trigger(queued), 30);
    }, DURATION[pulse.type]);
    return () => window.clearTimeout(timer);
  }, [pulse, trigger]);

  return { pulse, trigger };
}
