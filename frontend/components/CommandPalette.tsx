"use client";

import { useEffect } from "react";

export interface PaletteCommand {
  label: string;
  hint: string;
  run: () => void;
}

export function CommandPalette({
  open,
  commands,
  onClose,
}: {
  open: boolean;
  commands: PaletteCommand[];
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose, open]);
  if (!open) return null;
  return <div className="palette-backdrop" onMouseDown={onClose}><section className="command-palette" role="dialog" aria-modal="true" aria-label="Limit X command palette" onMouseDown={(event) => event.stopPropagation()}><header><span>Limit X command palette</span><kbd>Esc</kbd></header><div>{commands.map((command) => <button key={command.label} onClick={() => { command.run(); onClose(); }}><strong>{command.label}</strong><span>{command.hint}</span><i>↵</i></button>)}</div><footer><span>Navigation and simulation controls only</span><b>No shortcut submits an order</b></footer></section></div>;
}
