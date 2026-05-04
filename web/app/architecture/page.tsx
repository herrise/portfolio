"use client";

import { useEffect, useState } from "react";
import LambdaDiagram from "@/components/LambdaDiagram";

interface LayerInfo {
  name: string;
  color: string;
  storage: string;
  latency: string;
  accuracy: string;
  description: string;
  tech: string[];
  endpoints: string[];
}

export default function ArchitecturePage() {
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [active, setActive] = useState<string | undefined>();

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${apiUrl}/api/pipeline/architecture`)
      .then((r) => r.json())
      .then((json) => setLayers(json.layers || []))
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Lambda Architecture</h1>
        <p className="text-gray-500 mt-1">
          This pipeline demonstrates the Lambda Architecture pattern —
          a hybrid approach combining real-time streaming (speed layer) with
          batch processing for accuracy and completeness.
        </p>
      </header>

      {/* Interactive Diagram */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-sm font-semibold mb-4 uppercase tracking-wider text-gray-400">
          Pipeline Topology
        </h2>
        <LambdaDiagram activeLayer={active} />
        <div className="flex gap-4 mt-4 justify-center">
          {layers.map((l) => (
            <button
              key={l.name}
              onMouseEnter={() => setActive(l.name === "Speed Layer" ? "speed" : l.name === "Batch Layer" ? "batch" : l.name === "Serving Layer" ? "serving" : undefined)}
              onMouseLeave={() => setActive(undefined)}
              className="text-xs px-3 py-1 rounded-full border transition-all"
              style={{
                borderColor: l.color,
                backgroundColor: active === (l.name === "Speed Layer" ? "speed" : l.name === "Batch Layer" ? "batch" : l.name === "Serving Layer" ? "serving" : undefined) ? l.color + "20" : "transparent",
              }}
            >
              {l.name}
            </button>
          ))}
        </div>
      </section>

      {/* Layer Detail Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {layers.map((layer) => (
          <div
            key={layer.name}
            className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3"
            style={{ borderTopColor: layer.color, borderTopWidth: 3 }}
          >
            <h3 className="font-bold" style={{ color: layer.color }}>
              {layer.name}
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">Storage</span>
                <p className="font-mono">{layer.storage}</p>
              </div>
              <div>
                <span className="text-gray-500">Latency</span>
                <p className="font-mono">{layer.latency}</p>
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">Accuracy</span>
                <p className="font-mono">{layer.accuracy}</p>
              </div>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">{layer.description}</p>
            <div>
              <h4 className="text-xs text-gray-500 mb-1">Tech Stack</h4>
              <ul className="text-xs font-mono space-y-0.5">
                {layer.tech.map((t) => (
                  <li key={t} className="text-gray-300">&#x2022; {t}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs text-gray-500 mb-1">Endpoints</h4>
              <ul className="text-xs font-mono space-y-0.5">
                {layer.endpoints.map((e) => (
                  <li key={e} className="text-green-400">{e}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </section>

      {/* Lambda Architecture Explanation */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
          How Lambda Architecture Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
          <div className="space-y-2">
            <div className="w-3 h-3 rounded-full bg-speed" />
            <h3 className="font-bold text-speed">1. Speed Layer</h3>
            <p className="text-gray-400">
              Processes data in real-time with low latency. Uses Redis as an
              in-memory cache with pub/sub for instant updates. Sacrifices
              some accuracy for speed — data has a 90-second TTL. Think of it
              as the "approximate" view.
            </p>
          </div>
          <div className="space-y-2">
            <div className="w-3 h-3 rounded-full bg-batch" />
            <h3 className="font-bold text-batch">2. Batch Layer</h3>
            <p className="text-gray-400">
              Runs periodically (every 5 minutes) to compute accurate,
              historical views. Uses dbt to transform raw data into a
              dimensional model (star schema) with data quality tests.
              This is the "authoritative" view.
            </p>
          </div>
          <div className="space-y-2">
            <div className="w-3 h-3 rounded-full bg-merged" />
            <h3 className="font-bold text-merged">3. Serving Layer</h3>
            <p className="text-gray-400">
              Merges speed and batch views — real-time data fills recent
              gaps while batch provides historical completeness. The API
              lets you query each layer separately or the merged result.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
