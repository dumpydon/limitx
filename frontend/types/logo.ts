export type LogoPulse = "idle" | "buy" | "sell" | "trade" | "sweep" | "reject" | "resync";

export interface LogoPulseState {
  type: LogoPulse;
  id: number;
}

