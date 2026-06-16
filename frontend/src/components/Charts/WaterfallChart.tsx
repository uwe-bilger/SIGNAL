import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer, ReferenceLine,
} from "recharts";

interface WaterfallItem {
  version_id: string;
  total_units: number;
  delta_units: number;
}

interface Props {
  data: WaterfallItem[];
}

function fmt(n: number) {
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function WaterfallChart({ data }: Props) {
  if (!data.length) return <div className="text-text-secondary text-sm p-4">No data</div>;

  const chartData = data.map((item, i) => {
    const base = i === 0 ? 0 : data[i - 1].total_units;
    return {
      name: item.version_id,
      base,
      value: item.delta_units === 0 ? item.total_units : Math.abs(item.delta_units),
      delta: item.delta_units,
      total: item.total_units,
      isFirst: i === 0,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt} tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#1A1D27", border: "1px solid #2A2D3A", borderRadius: 8 }}
          labelStyle={{ color: "#F1F5F9" }}
          formatter={(val: any, name: any, props: any) => {
            if (name === "base") return null;
            return [fmt(props.payload.total), "Total Units"];
          }}
        />
        <Bar dataKey="base" stackId="a" fill="transparent" />
        <Bar dataKey="value" stackId="a" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.isFirst ? "#6366F1" : entry.delta >= 0 ? "#10B981" : "#EF4444"}
            />
          ))}
        </Bar>
        <ReferenceLine y={0} stroke="#2A2D3A" />
      </BarChart>
    </ResponsiveContainer>
  );
}
