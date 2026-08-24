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
  // Match the live reference's rigid 3px cell + 1px gap at CSS scale.
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
