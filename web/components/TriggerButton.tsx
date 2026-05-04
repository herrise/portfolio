"use client";

import { useState } from "react";

export default function TriggerButton({ layer }: { layer: "speed" | "batch" }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const color = layer === "speed" ? "border-speed text-speed bg-speed/10" : "border-batch text-batch bg-batch/10";

  const trigger = async () => {
    setLoading(true);
    setResult(null);
    try {
      const r = await fetch(`${apiUrl}/api/pipeline/trigger/${layer}`, { method: "POST" });
      const data = await r.json();
      setResult(data.ok ? `Triggered (${data.subscribers_reached} subscribers)` : `Error: ${data.error}`);
    } catch (e) {
      setResult("Connection failed");
    }
    setLoading(false);
    setTimeout(() => setResult(null), 3000);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={trigger}
        disabled={loading}
        className={`text-xs px-4 py-1.5 rounded-full border transition-all hover:brightness-125 disabled:opacity-50 ${color}`}
      >
        {loading ? "Sending..." : `Trigger ${layer}`}
      </button>
      {result && <span className="text-xs text-gray-400">{result}</span>}
    </div>
  );
}
