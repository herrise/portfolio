"use client";

import { useEffect, useState } from "react";

interface Ticker {
  symbol: string;
  price_usd: number;
  change_24h_pct: number;
}

export default function LiveTickerBar() {
  const [tickers, setTickers] = useState<Ticker[]>([]);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "";
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      ws = new WebSocket(`${wsUrl}/ws/live`);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "prices") {
            setTickers(msg.data || []);
          }
        } catch {}
      };

      ws.onclose = () => {
        reconnectTimer = setTimeout(connect, 3000);
      };
    }

    connect();
    return () => {
      ws?.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

  if (tickers.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center text-sm text-gray-500">
        Waiting for live data... (start stream-ingester container)
      </div>
    );
  }

  // Duplicate for seamless scroll
  const items = [...tickers, ...tickers];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <div className="flex ticker-track gap-8 py-3 px-4 whitespace-nowrap text-sm">
        {items.map((t, i) => (
          <span key={`${t.symbol}-${i}`} className="flex items-center gap-2">
            <span className="font-mono font-bold uppercase">{t.symbol}</span>
            <span className="text-gray-300">${t.price_usd?.toFixed(2)}</span>
            <span className={t.change_24h_pct >= 0 ? "text-green-400" : "text-red-400"}>
              {t.change_24h_pct >= 0 ? "+" : ""}{t.change_24h_pct?.toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
