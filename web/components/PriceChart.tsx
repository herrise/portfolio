"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface PricePoint {
  snapshot_ts: string;
  price_usd: number;
}

const COLORS: Record<string, string> = {
  speed: "#F59E0B",
  batch: "#3B82F6",
  merged: "#10B981",
};

export default function PriceChart({
  view,
  symbol,
}: {
  view: "speed" | "batch" | "merged";
  symbol: string;
}) {
  const [data, setData] = useState<PricePoint[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${apiUrl}/api/prices/${symbol}/history?hours=24`)
      .then((r) => r.json())
      .then((json) => {
        const pts = (json.data || []).map((d: PricePoint) => ({
          ...d,
          time: new Date(d.snapshot_ts).toLocaleTimeString(),
        }));
        setData(pts);
      })
      .catch(() => {});
  }, [symbol]);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold mb-3 uppercase tracking-wide text-gray-400">
        {symbol} — 24h History
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
          <XAxis dataKey="time" stroke="#6B7280" tick={{ fontSize: 11 }} />
          <YAxis stroke="#6B7280" tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: "8px" }}
            labelStyle={{ color: "#E5E7EB" }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="price_usd"
            name="Price (USD)"
            stroke={COLORS[view] || COLORS.merged}
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
