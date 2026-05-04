"use client";

import { useEffect, useState } from "react";

interface DbtStatus {
  last_event: string;
  status: string;
  detail: string;
  at: string;
}

interface LastLog {
  last_event: string;
  status: string;
  detail: string;
  at: number | string;
}

interface LayerHealth {
  healthy: boolean;
  last_run_id?: number;
  last_run_at?: string;
  rows_ingested_total?: number;
  tickers_in_cache?: number;
  status?: string;
  triggered_by?: string;
  dbt?: DbtStatus;
  last_log?: LastLog;
}

interface Status {
  batch_layer: LayerHealth;
  speed_layer: LayerHealth;
}

function formatTs(at: number | string | undefined): string {
  if (!at) return "";
  const ts = typeof at === "number" ? at * 1000 : new Date(at).getTime();
  return new Date(ts).toLocaleTimeString();
}

export default function PipelineHealth() {
  const [status, setStatus] = useState<Status | null>(null);
  const [triggering, setTriggering] = useState<Record<string, boolean>>({});

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    const fetchStatus = () =>
      fetch(`${apiUrl}/api/pipeline/status`)
        .then((r) => r.json())
        .then(setStatus)
        .catch(() => {});

    fetchStatus();
    const id = setInterval(fetchStatus, 10000);
    return () => clearInterval(id);
  }, [apiUrl]);

  const triggerIngest = async (layer: string) => {
    setTriggering((prev) => ({ ...prev, [layer]: true }));
    try {
      const r = await fetch(`${apiUrl}/api/pipeline/trigger/${layer}`, { method: "POST" });
      const data = await r.json();
      if (!data.ok) alert(`Trigger failed: ${data.error}`);
    } catch {
      alert("Trigger failed — check API connection");
    }
    setTriggering((prev) => ({ ...prev, [layer]: false }));
  };

  if (!status) return null;

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className={`bg-gray-900 border rounded-lg p-4 ${status.speed_layer.healthy ? "border-gray-700" : "border-red-700"}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${status.speed_layer.healthy ? "bg-speed" : "bg-red-500 animate-pulse"}`}
            />
            <span className="text-sm font-semibold">Speed Layer (Redis)</span>
          </div>
          <button
            onClick={() => triggerIngest("speed")}
            disabled={triggering.speed}
            className="text-xs px-3 py-1 rounded-full bg-speed/20 hover:bg-speed/30 text-speed border border-speed/30 transition-all disabled:opacity-50"
          >
            {triggering.speed ? "..." : "Trigger Now"}
          </button>
        </div>
        <p className="text-xs text-gray-500">{status.speed_layer.tickers_in_cache ?? 0} tickers cached</p>
        {status.speed_layer.last_log && (
          <p className="text-xs text-gray-600 mt-0.5 font-mono">
            {status.speed_layer.last_log.last_event} · {formatTs(status.speed_layer.last_log.at)}
          </p>
        )}
      </div>

      <div className={`bg-gray-900 border rounded-lg p-4 ${status.batch_layer.healthy ? "border-gray-700" : "border-red-700"}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${status.batch_layer.healthy ? "bg-batch" : "bg-red-500 animate-pulse"}`}
            />
            <span className="text-sm font-semibold">Batch Layer (DuckDB + dbt)</span>
          </div>
          <button
            onClick={() => triggerIngest("batch")}
            disabled={triggering.batch}
            className="text-xs px-3 py-1 rounded-full bg-batch/20 hover:bg-batch/30 text-batch border border-batch/30 transition-all disabled:opacity-50"
          >
            {triggering.batch ? "..." : "Trigger Now"}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          {status.batch_layer.last_run_at
            ? `Run #${status.batch_layer.last_run_id} · ${status.batch_layer.rows_ingested_total} rows · ${status.batch_layer.triggered_by || "scheduler"}`
            : "No data yet"}
        </p>
        {status.batch_layer.dbt && (
          <p className="text-xs text-gray-600 mt-0.5 font-mono">
            dbt: {status.batch_layer.dbt.status} · {status.batch_layer.dbt.last_event} · {new Date(status.batch_layer.dbt.at).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
