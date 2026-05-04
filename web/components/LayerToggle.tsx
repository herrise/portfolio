"use client";

type View = "speed" | "batch" | "merged";

export default function LayerToggle({
  view,
  onChange,
}: {
  view: View;
  onChange: (v: View) => void;
}) {
  const options: { value: View; label: string; color: string }[] = [
    { value: "speed", label: "Speed (Redis)", color: "border-speed bg-speed/10" },
    { value: "batch", label: "Batch (DuckDB)", color: "border-batch bg-batch/10" },
    { value: "merged", label: "Merged", color: "border-merged bg-merged/10" },
  ];

  return (
    <div className="flex gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-4 py-1.5 rounded-full text-sm border transition-all ${
            view === opt.value
              ? `${opt.color} border-2 font-semibold`
              : "border-gray-700 text-gray-500 hover:border-gray-500"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
