"use client";

export default function LambdaDiagram({ activeLayer }: { activeLayer?: string }) {
  const layers = [
    { id: "ingest", label: "CoinGecko API", x: 50, y: 5, w: 40, color: "#6B7280" },
    { id: "speed", label: "Speed Layer\n(Redis)", x: 5, y: 30, w: 35, color: "#F59E0B" },
    { id: "batch", label: "Batch Layer\n(DuckDB + dbt)", x: 55, y: 30, w: 40, color: "#3B82F6" },
    { id: "serving", label: "Serving Layer\n(FastAPI)", x: 5, y: 65, w: 90, color: "#10B981" },
    { id: "web", label: "Next.js Dashboard", x: 25, y: 90, w: 50, color: "#8B5CF6" },
  ];

  const isActive = (id: string) => !activeLayer || activeLayer === id;

  return (
    <div className="relative w-full" style={{ paddingBottom: "55%" }}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full">
        {/* Lines */}
        <line x1="70" y1="15" x2="20" y2="30" stroke="#374151" strokeWidth={0.4} />
        <line x1="70" y1="15" x2="75" y2="30" stroke="#374151" strokeWidth={0.4} />
        <line x1="20" y1="45" x2="20" y2="65" stroke="#374151" strokeWidth={0.4} />
        <line x1="75" y1="45" x2="75" y2="65" stroke="#374151" strokeWidth={0.4} />
        <line x1="50" y1="80" x2="50" y2="90" stroke="#374151" strokeWidth={0.4} />
        <text x="62" y="23" fill="#6B7280" fontSize={2} textAnchor="middle">fork</text>

        {layers.map((l) => (
          <g key={l.id}>
            <rect
              x={l.x}
              y={l.y}
              width={l.w}
              height={14}
              rx={2}
              fill={l.color}
              fillOpacity={isActive(l.id) ? 0.2 : 0.05}
              stroke={l.color}
              strokeOpacity={isActive(l.id) ? 0.8 : 0.2}
              strokeWidth={0.5}
            />
            <text
              x={l.x + l.w / 2}
              y={l.y + 6}
              fill={isActive(l.id) ? l.color : "#374151"}
              fontSize={2.2}
              textAnchor="middle"
              dominantBaseline="middle"
              fontWeight={600}
            >
              {l.label.split("\n")[0]}
            </text>
            {l.label.includes("\n") && (
              <text
                x={l.x + l.w / 2}
                y={l.y + 10}
                fill={isActive(l.id) ? l.color : "#374151"}
                fontSize={2}
                textAnchor="middle"
                dominantBaseline="middle"
                fillOpacity={0.7}
              >
                {l.label.split("\n")[1]}
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
