import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

interface Props {
  data: any[];
  bars: { key: string; color: string; label: string }[];
  xKey?: string;
  stacked?: boolean;
}

function fmt(n: number) {
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function BarStackChart({ data, bars, xKey = "name", stacked = false }: Props) {
  if (!data.length) return <div className="text-text-secondary text-sm p-4">No data</div>;
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt} tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#1A1D27", border: "1px solid #2A2D3A", borderRadius: 8 }}
          labelStyle={{ color: "#F1F5F9" }}
          formatter={(val: any) => [fmt(Number(val)), ""]}
        />
        <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
        {bars.map(b => (
          <Bar
            key={b.key}
            dataKey={b.key}
            fill={b.color}
            name={b.label}
            stackId={stacked ? "a" : undefined}
            radius={stacked ? undefined : [3, 3, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
