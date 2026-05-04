"use client";

import { useEffect, useState } from "react";

interface Ticker {
  symbol: string;
  price_usd: number;
  volume_24h: number;
  market_cap: number;
  price_change_24h_pct: number;
  market_cap_rank: number;
}

export default function TickerTable({ view }: { view: "speed" | "batch" | "merged" }) {
  const [tickers, setTickers] = useState<Ticker[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${apiUrl}/api/prices/latest?view=${view}`)
      .then((r) => r.json())
      .then((json) => setTickers(json.data || []))
      .catch(() => {});
  }, [view]);

  if (tickers.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 text-center text-sm text-gray-500">
        No data yet — run the batch ingester to populate the pipeline
      </div>
    );
  }

  const fmtB = (v: number) => {
    if (!v) return "—";
    if (v > 1e9) return `$${(v / 1e9).toFixed(2)}B`;
    if (v > 1e6) return `$${(v / 1e6).toFixed(2)}M`;
    return `$${v.toFixed(2)}`;
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left text-gray-500 text-xs uppercase tracking-wider">
            <th className="p-3">#</th>
            <th className="p-3">Symbol</th>
            <th className="p-3 text-right">Price</th>
            <th className="p-3 text-right">24h Change</th>
            <th className="p-3 text-right">Volume (24h)</th>
            <th className="p-3 text-right">Market Cap</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((t, i) => (
            <tr key={t.symbol} className="border-b border-gray-800/50 hover:bg-gray-800/30">
              <td className="p-3 text-gray-500">{t.market_cap_rank ?? i + 1}</td>
              <td className="p-3 font-mono font-bold uppercase">{t.symbol}</td>
              <td className="p-3 text-right font-mono">${t.price_usd?.toFixed(2)}</td>
              <td className={`p-3 text-right font-mono ${(t.price_change_24h_pct ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {(t.price_change_24h_pct ?? 0) >= 0 ? "+" : ""}{t.price_change_24h_pct?.toFixed(2)}%
              </td>
              <td className="p-3 text-right text-gray-400">{fmtB(t.volume_24h)}</td>
              <td className="p-3 text-right text-gray-400">{fmtB(t.market_cap)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
