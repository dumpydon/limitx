# Limit X — Dot-Matrix Wordmark + Footer Curtain Bundle

This is a portable implementation handoff for the exact closing visual used in Limit X:

1. `Limit X` is rasterized into a regular matrix of square cells.
2. Only cells inside the glyph mask are drawn.
3. Dim cells stay visible at rest.
4. A slow Simplex field illuminates cells as green or red energy moves through the letters.
5. The wordmark sits in a fixed bottom stage behind the normal page.
6. The normal page is an opaque foreground layer.
7. A transparent spacer lets the foreground scroll away and progressively uncover the fixed stage.

Copy this document into another Codex thread when reproducing the effect. Preserve the separation:

```text
dot animation = canvas + glyph mask + time field
curtain reveal = CSS layering + fixed stage + transparent spacer
```

Do not replace the curtain with a normal footer, a scroll-driven opacity fade, or a particle field.
The letters themselves must be made from cells.

## Visual contract

Use these values unless the target project has a deliberate responsive override:

| Detail | Value |
|---|---|
| Typeface | Geist Mono variable font, weight `640` |
| Text mask | `Limit X` |
| Limit/X visible gap | `0.75×` the normal visible gap |
| Cell size | `3px × 3px` |
| Cell spacing | `1px` gap (`4px` grid step) |
| Idle color | `rgba(255,255,255,.04)` |
| Buy/green cell | `#10b981` |
| Sell/red cell | `#ff6b7c` |
| Red selection | Stable per-cell hash, `34%` of active cells |
| Active threshold | `0.24` |
| Simplex scale | `0.002` |
| Noise blend | `0.7` static hash / animated noise |
| Travel speed | `0.5` time units per second |
| Canvas DPR cap | `2` |
| Visibility margin | `200px` |
| Resize debounce | `120ms` |
| Curtain stage | `clamp(440px, 82vh, 780px)` |
| Visible wordmark stage | `90%` width and `90%` height of curtain stage |
| Reveal spacer | stage height plus `10px` |

The `640` weight, 0.75× gap, 90% stage sizing, and red cells are part of the current Limit X
version. The original Explee-style animation is otherwise kept as a binary idle/active matrix:
there is no neon blur layer and no random DOM particle cloud.

## Required layer geometry

The DOM must have this relationship:

```text
viewport
┌────────────────────────────────────────────┐
│ fixed stage, z-index: 0                    │
│   dim/active dot-matrix Limit X             │
│                                            │
│ normal page surface, z-index: 1             │
│   header, panels, controls, footer text     │  ← opaque foreground
│                                            │
│ transparent reveal spacer after page      │
└────────────────────────────────────────────┘
```

The stage is a sibling of the main page, not a child of the opaque page surface. The stage remains
fixed to the bottom of the viewport while the page surface scrolls. At the end of the document the
page surface ends roughly `10px` above the stage top, so the complete wordmark is exposed.

The reveal is geometric. Do not update React state on scroll, do not map glow position to scroll,
and do not use `opacity: 0 → 1` as the main effect.

## Font setup

The wordmark is based on Geist Mono. In a portable project, vendor the official variable webfont
and load it through `next/font/local`:

```bash
mkdir -p frontend/app/fonts
curl -L 'https://raw.githubusercontent.com/vercel/geist-font/main/fonts/GeistMono/webfonts/GeistMono%5Bwght%5D.woff2' \
  -o frontend/app/fonts/GeistMono-Variable.woff2
```

For an App Router `app/layout.tsx`:

````tsx
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistMono = localFont({
  src: "./fonts/GeistMono-Variable.woff2",
  variable: "--font-wordmark",
  display: "swap",
  preload: true,
});

export const metadata: Metadata = {
  title: "Your project",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={geistMono.variable}>
      <body>{children}</body>
    </html>
  );
}
````

The current Limit X repository uses the same variable name with Next's bundled font asset:
`../node_modules/next/dist/next-devtools/server/font/geist-mono-latin.woff2`. In another project,
the portable vendored path above is safer. `glyphMask.ts` reads `--font-wordmark` at runtime.

## Minimal pulse type

The current component receives market pulse metadata so the canvas can expose the latest event for
the surrounding logo system. The pulse does not control the ambient dot-field animation.

````ts
export type LogoPulse = "idle" | "buy" | "sell" | "trade" | "sweep" | "reject" | "resync";

export interface LogoPulseState {
  type: LogoPulse;
  id: number;
}
````

If the host project has no market event system, pass `{ type: "idle", id: 0 }` permanently. Do not
remove the canvas animation or make it dependent on live events.

## File 1 — `components/dot-matrix/energyField.ts`

This is the CPU equivalent of the Simplex shader field. The constants and order of operations are
intentional; changing them changes the Explee-like cadence and spatial coherence.

````ts
const C_X = 0.211324865405187;
const C_Y = 0.366025403784439;
const C_Z = -0.577350269189626;
const C_W = 0.024390243902439;

function fract(value: number): number {
  return value - Math.floor(value);
}

function mod289(value: number): number {
  return value - Math.floor(value / 289) * 289;
}

function permute(value: number): number {
  return mod289(((value * 34) + 1) * value);
}

function simplexCorner(permutation: number, x: number, y: number): number {
  let magnitude = Math.max(0.5 - x * x - y * y, 0);
  magnitude *= magnitude;
  magnitude *= magnitude;
  const gradientX = 2 * fract(permutation * C_W) - 1;
  const h = Math.abs(gradientX) - 0.5;
  const offsetX = Math.floor(gradientX + 0.5);
  const a0 = gradientX - offsetX;
  magnitude *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  return magnitude * (a0 * x + h * y);
}

/** CPU equivalent of the Simplex shader used by the live reference. */
export function simplexNoise(xInput: number, yInput: number): number {
  let iX = Math.floor(xInput + (xInput + yInput) * C_Y);
  let iY = Math.floor(yInput + (xInput + yInput) * C_Y);
  const x0 = xInput - iX + (iX + iY) * C_X;
  const y0 = yInput - iY + (iX + iY) * C_X;
  const i1X = x0 > y0 ? 1 : 0;
  const i1Y = x0 > y0 ? 0 : 1;
  const x1 = x0 + C_X - i1X;
  const y1 = y0 + C_X - i1Y;
  const x2 = x0 + C_Z;
  const y2 = y0 + C_Z;

  iX = mod289(iX);
  iY = mod289(iY);
  const p0 = permute(permute(iY) + iX);
  const p1 = permute(permute(iY + i1Y) + iX + i1X);
  const p2 = permute(permute(iY + 1) + iX + 1);

  const raw = 130 * (
    simplexCorner(p0, x0, y0) +
    simplexCorner(p1, x1, y1) +
    simplexCorner(p2, x2, y2)
  );
  return raw * 0.5 + 0.5;
}
````

## File 2 — `components/dot-matrix/glyphMask.ts`

This rasterizes the actual typeface once per resize, samples only cells whose center falls inside
the glyph mask, and stores stable cell metadata. The custom composition gives the `Limit–X` gap
the current 0.75× visible spacing.

````ts
export interface DotCloud {
  width: number;
  height: number;
  step: number;
  size: number;
  count: number;
  positions: Float32Array;
  cells: Uint16Array;
  staticNoise: Float32Array;
  colorNoise: Float32Array;
}

function hash(x: number, y: number): number {
  const value = Math.sin(x * 127.1 + y * 311.7) * 43_758.5453;
  return value - Math.floor(value);
}

/** Rasterize once, then retain only rigid grid cells that fall inside the glyph mask. */
export function createDotCloud(width: number, height: number): DotCloud {
  const mask = document.createElement("canvas");
  mask.width = Math.max(1, Math.round(width));
  mask.height = Math.max(1, Math.round(height));
  const context = mask.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas 2D context is unavailable");

  const firstPart = "Limit";
  const secondPart = "X";
  const maxWidth = width * 0.92;
  let fontSize = height * 0.6;
  const configuredFont = getComputedStyle(document.documentElement)
    .getPropertyValue("--font-wordmark")
    .trim();
  const fontFamily = configuredFont || '"Geist Mono", "SFMono-Regular", monospace';
  context.font = `640 ${fontSize}px ${fontFamily}`;
  const reducedGap = (left: TextMetrics, right: TextMetrics, normalAdvance: number) => {
    const leftRightBearing = left.width - left.actualBoundingBoxRight;
    const normalVisibleGap = leftRightBearing + normalAdvance - right.actualBoundingBoxLeft;
    const targetVisibleGap = normalVisibleGap * 0.75;
    return Math.max(0, targetVisibleGap - leftRightBearing + right.actualBoundingBoxLeft);
  };
  const measureComposition = () => {
    const first = context.measureText(firstPart);
    const second = context.measureText(secondPart);
    const spaceAdvance = context.measureText(" ").width;
    return { first, second, gapAdvance: reducedGap(first, second, spaceAdvance) };
  };
  let composition = measureComposition();
  const initialWidth = composition.first.width + composition.gapAdvance + composition.second.width;
  if (initialWidth > maxWidth) fontSize *= maxWidth / initialWidth;
  context.font = `640 ${fontSize}px ${fontFamily}`;
  composition = measureComposition();
  const visibleLeft = -composition.first.actualBoundingBoxLeft;
  const visibleRight = composition.first.width + composition.gapAdvance + composition.second.actualBoundingBoxRight;
  const wordStart = width / 2 - (visibleLeft + visibleRight) / 2;
  context.textAlign = "left";
  context.textBaseline = "middle";
  context.fillStyle = "#fff";
  context.fillText(firstPart, wordStart, height / 2 + fontSize * 0.02);
  context.fillText(
    secondPart,
    wordStart + composition.first.width + composition.gapAdvance,
    height / 2 + fontSize * 0.02,
  );

  const pixels = context.getImageData(0, 0, mask.width, mask.height).data;
  // 3px cell + 1px gap at CSS scale.
  const size = 3;
  const step = 4;
  const columns = Math.floor((width + 1) / step);
  const rows = Math.floor((height + 1) / step);
  const gridWidth = columns > 0 ? columns * size + (columns - 1) : 0;
  const gridHeight = rows > 0 ? rows * size + (rows - 1) : 0;
  const offsetX = Math.round((width - gridWidth) / 2);
  const offsetY = Math.round((height - gridHeight) / 2);
  const coordinates: number[] = [];
  const cells: number[] = [];
  const staticNoise: number[] = [];
  const colorNoise: number[] = [];
  for (let row = 0; row < rows; row += 1) {
    const y = offsetY + row * step;
    for (let column = 0; column < columns; column += 1) {
      const x = offsetX + column * step;
      const pixelX = Math.min(mask.width - 1, Math.round(x + size / 2));
      const pixelY = Math.min(mask.height - 1, Math.round(y + size / 2));
      if (pixels[(pixelY * mask.width + pixelX) * 4 + 3] < 96) continue;
      coordinates.push(x, y);
      cells.push(column, row);
      staticNoise.push(hash(column, row));
      colorNoise.push(hash(column + 73, row + 157));
    }
  }
  const count = staticNoise.length;
  return {
    width,
    height,
    step,
    size,
    count,
    positions: Float32Array.from(coordinates),
    cells: Uint16Array.from(cells),
    staticNoise: Float32Array.from(staticNoise),
    colorNoise: Float32Array.from(colorNoise),
  };
}
````

## File 3 — `components/DotMatrixWordmark.tsx`

The canvas draws the complete dim matrix first, then redraws active cells with stable red/green
selection. The animation is independent from scrolling. `IntersectionObserver` pauses it when the
stage is outside the viewport; `ResizeObserver` rebuilds the mask after a debounced size change.

````tsx
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
````

## Curtain CSS

Add these rules to the host project's stylesheet. `--bg` must be the same dark page color used by
the foreground surface and stage; this prevents a visible black rectangle. The `90%` child is the
current Limit X size pass.

````css
.footer-curtain-content {
  position: relative;
  z-index: 1;
  background: radial-gradient(circle at 50% -20%, #1d253a 0, transparent 38%), var(--bg);
}

.footer-curtain-stage {
  position: fixed;
  z-index: 0;
  inset: auto 0 0;
  width: 100%;
  height: clamp(440px, 82vh, 780px);
  display: grid;
  place-items: center;
  overflow: hidden;
  pointer-events: none;
  background: var(--bg);
}

.footer-curtain-stage .dot-wordmark-section {
  width: 90%;
  height: 90%;
  margin: 0;
}

.footer-curtain-spacer {
  position: relative;
  z-index: 0;
  height: calc(clamp(440px, 82vh, 780px) + 10px);
  min-height: 450px;
  background: transparent;
}

.dot-wordmark-section {
  position: relative;
  width: calc(100% + 48px);
  height: clamp(440px, 82vh, 780px);
  margin: 54px -24px -20px;
  overflow: hidden;
  background: transparent;
}

.dot-wordmark-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

@media (max-width: 760px) {
  .footer-curtain-stage {
    height: clamp(360px, 66vh, 520px);
  }

  .footer-curtain-spacer {
    height: calc(clamp(360px, 66vh, 520px) + 10px);
    min-height: 370px;
  }

  .dot-wordmark-section {
    width: calc(100% + 16px);
    height: clamp(360px, 66vh, 520px);
    margin: 36px -8px -20px;
  }
}
````

## Page integration

Move the existing wordmark out of the normal page surface and make it a sibling fixed stage. Keep
the page's normal footer text inside the foreground surface. Any fixed inspectors or command
palettes can remain outside the main surface with their own higher z-index.

````tsx
return (
  <>
    <div className="footer-curtain-stage">
      <DotMatrixWordmark pulse={logoPulse} />
    </div>

    <main className="app-shell footer-curtain-content">
      {/* all existing application content */}

      <footer className="app-footer">
        <span>Limit X / matching-engine observatory</span>
        <span>Python matcher · single writer · sequence-linked market data</span>
        <span>Simulation only</span>
      </footer>
    </main>

    <div className="footer-curtain-spacer" aria-hidden="true" />

    {/* existing fixed inspectors/palettes, if any */}
  </>
);
````

The stage must be before or after the main sibling with explicit z-indexes; DOM order should not be
used as the only layering mechanism. The foreground `main` needs an opaque background. If it is
transparent, the wordmark will leak through the whole application instead of behaving like a hidden
footer installation.

## What the user should experience

At the start of the page, the normal application is dominant and the fixed wordmark is covered. As
the user approaches the end, the bottom edge of the foreground page moves upward and the lower
portion of the dim matrix appears underneath it. More scrolling reveals more of the same running
canvas. At the final scroll position, the foreground surface ends just above the stage and the full
wordmark is visible. The cells continue animating throughout; scroll controls only how much is
visible.

## Validation checklist

Use the browser at desktop width and inspect these checkpoints:

- top of page: no wordmark leakage through the main surface;
- near the footer: a small lower portion begins to appear;
- 30–70% of the reveal: the foreground surface visibly passes over the wordmark;
- bottom: the full dim `Limit X` matrix is visible and comfortably above the browser edge;
- active cells remain sharp square cells, with green and red at equal full alpha;
- no extra dot grid outside the letters;
- resize rebuilds the mask without a layout jump;
- `prefers-reduced-motion: reduce` renders a static matrix and no RAF loop;
- scrolling does not change the glow phase or restart the canvas;
- the canvas has one `requestAnimationFrame` loop and no thousands of DOM nodes.

Useful runtime markers from the current component are `data-dot-count`, `data-grid-step`,
`data-cell-size`, `data-dpr`, and `data-animation` on the canvas.

## Common mistakes to avoid

1. Putting the fixed stage inside `.footer-curtain-content`: the opaque ancestor will hide it at
   every scroll position.
2. Leaving the spacer opaque: the reveal will never show the stage.
3. Using `position: sticky` or scroll React state without verifying geometry: this changes the
   Explee-style fixed-bottom behavior and can cause snapping.
4. Rendering normal HTML `Limit X` over a dot background: the glyph mask must be the only source of
   visible cells.
5. Using a different font weight or a fallback font: the sampled letter geometry changes.
6. Adding a large blur/glow pass: Explee's cells remain crisp; active color is the animation.
7. Tying the noise time to scroll: the field must keep moving when the user stops scrolling.
8. Rebuilding the cloud on every animation frame: build it only on mount, font readiness, resize,
   or motion-preference changes.
9. Giving the stage a different background from the page: this creates the black rectangle that
   the current Limit X implementation intentionally removed.

## Portable implementation order

1. Add and load Geist Mono.
2. Add `energyField.ts`.
3. Add `glyphMask.ts`.
4. Add `DotMatrixWordmark.tsx` and the pulse type.
5. Render the existing app inside `.footer-curtain-content`.
6. Add the fixed stage sibling and transparent spacer.
7. Add the CSS rules exactly, then adjust only the host page's `--bg` color.
8. Run the host project's lint, typecheck, and production build.
9. Compare top, mid, and bottom screenshots before changing any dimensions.

The animation and curtain are intentionally separate. If the host project has an existing logo,
market, or event system, integrate it through the `pulse` metadata only. Do not rewrite the canvas
field when adapting the surrounding page.
