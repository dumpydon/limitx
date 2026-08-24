"use client";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <main className="fatal-boundary"><span>LIMIT / X</span><h1>Visualization boundary isolated a failure</h1><p>The matching engine is separate from this browser rendering error. Reconnect the projection without changing engine state.</p><code>{error.message}</code><button onClick={reset}>Reconnect visualization</button></main>;
}
