import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistMono = localFont({
  src: "../node_modules/next/dist/next-devtools/server/font/geist-mono-latin.woff2",
  variable: "--font-wordmark",
  display: "swap",
  preload: true,
});

export const metadata: Metadata = {
  title: "Limit X — Market Microstructure Laboratory",
  description: "A deterministic exchange matching-engine and market-microstructure laboratory.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={geistMono.variable}>
      <body>{children}</body>
    </html>
  );
}
