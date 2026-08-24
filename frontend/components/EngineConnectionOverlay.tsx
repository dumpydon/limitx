import type { BackendStatus } from "@/types/market";

interface EngineConnectionOverlayProps {
  status: BackendStatus;
  onRetry: () => void;
}

export function EngineConnectionOverlay({ status, onRetry }: EngineConnectionOverlayProps) {
  if (status === "CONNECTED") return null;

  const timedOut = status === "TIMEOUT";
  const stateLabel = status === "CHECKING" ? "Checking engine availability…" : "Waking the simulation engine…";

  return (
    <div className="engine-connection-overlay" role={timedOut ? "alert" : "status"} aria-live="polite" aria-busy={!timedOut}>
      <section className="engine-connection-panel" aria-label="Limit X engine connection">
        <span className="engine-connection-kicker">Limit X · engine connection</span>
        <h1>Connecting to the Limit X engine</h1>
        <p>This demo uses a free-tier Render backend, which may sleep after a period of inactivity.</p>
        <p>Waking the engine may take up to about a minute.</p>
        <div className="engine-connection-track" aria-hidden="true"><span /></div>
        <div className="engine-connection-state">{timedOut ? "The simulation engine is taking longer than expected to respond." : stateLabel}</div>
        {timedOut ? <button type="button" onClick={onRetry}>Retry connection</button> : null}
      </section>
    </div>
  );
}
