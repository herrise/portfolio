"use client";

import { useState } from "react";
import LiveTickerBar from "@/components/LiveTickerBar";
import PriceChart from "@/components/PriceChart";
import TickerTable from "@/components/TickerTable";
import PipelineHealth from "@/components/PipelineHealth";
import LogPanel from "@/components/LogPanel";
import LayerToggle from "@/components/LayerToggle";

type View = "speed" | "batch" | "merged";

export default function Dashboard() {
  const [view, setView] = useState<View>("merged");
  const [logLayer, setLogLayer] = useState<"all" | "speed" | "batch">("all");

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      {/* Live ticker bar */}
      <section>
        <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-2">
          Live Ticker (Speed Layer · WebSocket)
        </h2>
        <LiveTickerBar />
      </section>

      {/* Pipeline health with trigger buttons */}
      <section>
        <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-2">
          Pipeline Health ·{" "}
          <span className="text-gray-600">Manual controls available on each layer card</span>
        </h2>
        <PipelineHealth />
      </section>

      {/* Chart + Table with layer toggle */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs uppercase tracking-widest text-gray-500">Market Data</h2>
          <LayerToggle view={view} onChange={setView} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PriceChart view={view} symbol="bitcoin" />
          <PriceChart view={view} symbol="ethereum" />
        </div>
        <TickerTable view={view} />
      </section>

      {/* Pipeline Monitoring Logs */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs uppercase tracking-widest text-gray-500">Pipeline Monitoring</h2>
          <div className="flex gap-2">
            {(["all", "speed", "batch"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLogLayer(l)}
                className={`px-3 py-1 rounded-full text-xs border transition-all ${
                  logLayer === l
                    ? "border-gray-400 bg-gray-700 text-white"
                    : "border-gray-700 text-gray-500 hover:border-gray-500"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
        <LogPanel layer={logLayer} />
      </section>
    </div>
  );
}
