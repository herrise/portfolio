"use client";

import { useEffect, useState } from "react";

interface LogEntry {
  id: number;
  ts: string;
  layer: string;
  event: string;
  status: string;
  detail: string;
  rows_affected: number;
}

const STATUS_COLORS: Record<string, string> = {
  success: "text-green-400",
  failed: "text-red-400",
  running: "text-yellow-400",
  healthy: "text-green-400",
};

const LAYER_COLORS: Record<string, string> = {
  speed: "text-speed",
  batch: "text-batch",
};

export default function LogPanel({ layer }: { layer: "all" | "speed" | "batch" }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
    const fetchLogs = () =>
      fetch(`${apiUrl}/api/pipeline/logs?layer=${layer}&limit=30`)
        .then((r) => r.json())
        .then((json) => setLogs(json.logs || []))
        .catch(() => {});

    fetchLogs();
    const id = setInterval(fetchLogs, 10000);
    return () => clearInterval(id);
  }, [layer]);

  if (logs.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center text-xs text-gray-600">
        No pipeline logs yet — waiting for data...
      </div>
    );
  }

  const displayed = expanded ? logs : logs.slice(0, 8);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <h3 className="text-xs uppercase tracking-wider text-gray-400">
          Pipeline Logs — {layer}
        </h3>
        {logs.length > 8 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-500 hover:text-white transition-colors"
          >
            {expanded ? "collapse" : `+${logs.length - 8} more`}
          </button>
        )}
      </div>
      <div className="max-h-80 overflow-y-auto">
        {displayed.map((entry) => (
          <div
            key={entry.id}
            className="flex items-start gap-3 px-4 py-1.5 border-b border-gray-800/30 text-xs font-mono hover:bg-gray-800/20"
          >
            <span className="text-gray-600 w-16 shrink-0">
              {new Date(entry.ts).toLocaleTimeString()}
            </span>
            <span className={`w-12 shrink-0 ${LAYER_COLORS[entry.layer] || "text-gray-400"}`}>
              [{entry.layer}]
            </span>
            <span className={`w-24 shrink-0 ${STATUS_COLORS[entry.status] || "text-gray-300"}`}>
              {entry.event}
            </span>
            <span className={`${entry.status === "failed" ? "text-red-400" : "text-gray-500"}`}>
              {entry.detail?.slice(0, 120)}
            </span>
            {entry.rows_affected > 0 && (
              <span className="text-gray-600 ml-auto shrink-0">{entry.rows_affected} rows</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
