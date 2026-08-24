"use client";

import { useEffect, useRef } from "react";
import type { LogoPulseState } from "@/types/logo";
import { createDotCloud, type DotCloud } from "./dot-matrix/glyphMask";
import { simplexNoise } from "./dot-matrix/energyField";

const ACCENT = "#10b981";
const SELL_ACCENT = "#ff6b7c";
const IDLE = "rgba(255,255,255,.04)";
const ACCENT_PERCENT = 0.24;
const NOISE_SCALE = 0.002;
const NOISE_BLEND = 0.7;
const TRAVEL_SPEED = 0.5;

function drawFrame(
  context: CanvasRenderingContext2D,
  cloud: DotCloud,
  elapsed: number,
): void {
  context.clearRect(0, 0, cloud.width, cloud.height);
  context.fillStyle = IDLE;
  for (let index = 0; index < cloud.count; index += 1) {
    context.fillRect(
      cloud.positions[index * 2],
      cloud.positions[index * 2 + 1],
      cloud.size,
      cloud.size,
    );
  }

  let activeColor = "";
  const travel = elapsed * TRAVEL_SPEED;
  for (let index = 0; index < cloud.count; index += 1) {
    const noise = simplexNoise(
      cloud.cells[index * 2] * NOISE_SCALE + travel,
      cloud.cells[index * 2 + 1] * NOISE_SCALE + travel,
    );
    const threshold = cloud.staticNoise[index] * (1 - NOISE_BLEND) + noise * NOISE_BLEND;
    if (threshold >= ACCENT_PERCENT) continue;
    const nextColor = cloud.colorNoise[index] < 0.34 ? SELL_ACCENT : ACCENT;
    if (nextColor !== activeColor) {
      context.fillStyle = nextColor;
      activeColor = nextColor;
    }
    context.fillRect(
      cloud.positions[index * 2],
      cloud.positions[index * 2 + 1],
      cloud.size,
      cloud.size,
    );
  }
}

export function DotMatrixWordmark({ pulse }: { pulse: LogoPulseState }) {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    canvasRef.current.dataset.marketPulse = pulse.type;
    canvasRef.current.dataset.marketPulseId = String(pulse.id);
  }, [pulse]);

  useEffect(() => {
    const section = sectionRef.current;
    const canvas = canvasRef.current;
    if (!section || !canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    let cloud: DotCloud | null = null;
    let frame = 0;
    let visible = false;
    let resizeTimer = 0;
    let startedAt = 0;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const render = (timestamp: number) => {
      if (!cloud) return;
      drawFrame(context, cloud, timestamp / 1_000 - startedAt);
      if (visible && !reducedMotion.matches) frame = requestAnimationFrame(render);
    };

    const rebuild = () => {
      const bounds = section.getBoundingClientRect();
      const width = Math.max(320, bounds.width);
      const height = Math.max(360, bounds.height);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      cloud = createDotCloud(width, height);
      canvas.dataset.dotCount = String(cloud.count);
      canvas.dataset.gridStep = cloud.step.toFixed(2);
      canvas.dataset.cellSize = cloud.size.toFixed(2);
      canvas.dataset.dpr = dpr.toFixed(2);
      if (reducedMotion.matches) drawFrame(context, cloud, 8.25);
      else drawFrame(context, cloud, startedAt ? performance.now() / 1_000 - startedAt : 0);
    };

    const start = () => {
      if (frame || reducedMotion.matches) {
        if (reducedMotion.matches) canvas.dataset.animation = "reduced";
        return;
      }
      canvas.dataset.animation = "running";
      startedAt = performance.now() / 1_000;
      frame = requestAnimationFrame(render);
    };

    const stop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      canvas.dataset.animation = "paused";
    };

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
      else stop();
    }, { rootMargin: "200px" });
    observer.observe(section);

    const resizeObserver = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(rebuild, 120);
    });
    resizeObserver.observe(section);

    const onMotionChange = () => {
      stop();
      rebuild();
      if (visible) start();
    };
    reducedMotion.addEventListener("change", onMotionChange);
    void document.fonts.ready.then(rebuild);
    rebuild();

    return () => {
      stop();
      observer.disconnect();
      resizeObserver.disconnect();
      reducedMotion.removeEventListener("change", onMotionChange);
      window.clearTimeout(resizeTimer);
    };
  }, []);

  return (
    <section ref={sectionRef} className="dot-wordmark-section" aria-label="Limit X dot-matrix wordmark">
      <canvas ref={canvasRef} className="dot-wordmark-canvas" role="img" aria-label="Limit X rendered entirely from illuminated square cells" />
    </section>
  );
}
