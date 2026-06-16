import React from "react";

interface Props {
  rows: string[];
  cols: string[];
  data: Record<string, Record<string, number>>;
  rowLabel?: string;
}

function cellColor(val: number, max: number) {
  if (!val || !max) return "bg-surface";
  const intensity = Math.min(val / max, 1);
  if (intensity > 0.75) return "bg-primary/60";
  if (intensity > 0.5) return "bg-primary/40";
  if (intensity > 0.25) return "bg-primary/25";
  return "bg-primary/10";
}

function fmt(n: number) {
  if (!n) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function HeatmapTable({ rows, cols, data, rowLabel = "SKU" }: Props) {
  const allVals = rows.flatMap(r => cols.map(c => data[r]?.[c] || 0));
  const max = Math.max(...allVals, 1);

  if (!rows.length || !cols.length)
    return <div className="text-text-secondary text-sm p-4">No data</div>;

  return (
    <div className="overflow-auto">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left px-3 py-2 text-text-secondary font-medium sticky left-0 bg-surface z-10">
              {rowLabel}
            </th>
            {cols.map(c => (
              <th key={c} className="px-2 py-2 text-text-secondary font-medium text-right whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r} className="border-t border-border hover:bg-white/5">
              <td className="px-3 py-1.5 text-text-primary font-medium sticky left-0 bg-surface z-10 whitespace-nowrap">
                {r}
              </td>
              {cols.map(c => {
                const val = data[r]?.[c] || 0;
                return (
                  <td key={c} className={`px-2 py-1.5 text-right ${cellColor(val, max)} text-text-primary`}>
                    {fmt(val)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
