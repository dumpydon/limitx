import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Limit X — Market Microstructure Laboratory",
  description: "A deterministic exchange matching-engine and market-microstructure laboratory.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

