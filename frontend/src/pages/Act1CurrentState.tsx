import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";
import { BarStackChart } from "../components/Charts/BarStackChart";
import { LineCompareChart } from "../components/Charts/LineCompareChart";
import { HeatmapTable } from "../components/Charts/HeatmapTable";
import { ExceptionBadge } from "../components/Badges/ExceptionBadge";

interface Props { filters: Filters }

function KpiCard({ label, value, sub, color = "" }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="text-text-secondary text-xs font-medium uppercase tracking-wider mb-2">{label}</div>
      <div className={`text-2xl font-bold ${color || "text-text-primary"}`}>{value}</div>
      {sub && <div className="text-text-secondary text-xs mt-1">{sub}</div>}
    </div>
  );
}

function fmt(n: number) {
  if (!n && n !== 0) return "—";
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(Math.round(n));
}

function fmtDollar(n: number) {
  if (!n && n !== 0) return "—";
  if (Math.abs(n) >= 1_000_000) return "$" + (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return "$" + (n / 1_000).toFixed(0) + "K";
  return "$" + Math.round(n);
}

function fmtPct(n: number | null) {
  if (n === undefined || n === null || isNaN(n)) return "—";
  const sign = n >= 0 ? "+" : "";
  return sign + (n * 100).toFixed(1) + "%";
}

function sumField(rows: any[], field: string) {
  return rows.reduce((acc, r) => acc + (Number(r[field]) || 0), 0);
}

export function Act1CurrentState({ filters }: Props) {
  const [rows, setRows] = useState<any[]>([]);
  const [pyRows, setPyRows] = useState<any[]>([]);
  const [budgetRows, setBudgetRows] = useState<any[]>([]);
  const [skuMatrix, setSkuMatrix] = useState<any[]>([]);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fy = filters.fiscal_year || 2024;
    const v = filters.version_id || "LATEST_EST";
    const params: any = { fiscal_year: fy, version_id: v };
    if (filters.division) params.division = filters.division;
    if (filters.channel_type) params.channel_type = filters.channel_type;

    Promise.all([
      api.get("/api/plan/summary", { params }),
      api.get("/api/plan/summary", { params: { ...params, fiscal_year: fy - 1 } }),
      api.get("/api/plan/summary", { params: { ...params, version_id: "BUDGET" } }),
      api.get("/api/plan/top-skus", { params: { ...params, limit: 15 } }),
      api.get("/api/exceptions", { params: { fiscal_year: fy, division: filters.division } }),
    ]).then(([curR, pyR, budR, skuR, excR]) => {
      setRows(curR.data || []);
      setPyRows(pyR.data || []);
      setBudgetRows(budR.data || []);
      setSkuMatrix(skuR.data || []);
      setExceptions(excR.data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.version_id, filters.division, filters.channel_type]);

  // Aggregate totals
  const totalUnits = sumField(rows, "total_forecast_units");
  const totalDollars = sumField(rows, "total_forecast_dollars");
  const budgetUnits = sumField(budgetRows, "total_forecast_units");
  const pyUnits = sumField(pyRows, "total_forecast_units");
  const vsBudget = budgetUnits > 0 ? (totalUnits - budgetUnits) / budgetUnits : null;
  const vsPY = pyUnits > 0 ? (totalUnits - pyUnits) / pyUnits : null;

  // Monthly trend
  const byMonth: Record<number, { cur: number; py: number }> = {};
  rows.forEach(r => {
    const m = r.fiscal_month;
    if (!byMonth[m]) byMonth[m] = { cur: 0, py: 0 };
    byMonth[m].cur += Number(r.sell_in_units) || 0;
  });
  pyRows.forEach(r => {
    const m = r.fiscal_month;
    if (!byMonth[m]) byMonth[m] = { cur: 0, py: 0 };
    byMonth[m].py += Number(r.sell_in_units) || 0;
  });
  const trendData = Array.from({ length: 12 }, (_, i) => ({
    name: `M${i + 1}`,
    "This Year": byMonth[i + 1]?.cur || 0,
    "Prior Year": byMonth[i + 1]?.py || 0,
  }));

  // Build heatmap from top-skus matrix
  const skuTotals: Record<string, number> = {};
  skuMatrix.forEach((r: any) => {
    skuTotals[r.sku_id] = (skuTotals[r.sku_id] || 0) + (Number(r.forecast_units) || 0);
  });
  const top15Skus = Object.entries(skuTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map(([id]) => id);
  const accounts = Array.from(new Set(skuMatrix.map((r: any) => r.key_account_id))).slice(0, 8) as string[];
  const heatData: Record<string, Record<string, number>> = {};
  skuMatrix.forEach((r: any) => {
    if (!heatData[r.sku_id]) heatData[r.sku_id] = {};
    heatData[r.sku_id][r.key_account_id] = (heatData[r.sku_id][r.key_account_id] || 0) + Number(r.forecast_units);
  });

  // Top 10 SKUs bar
  const top10 = Object.entries(skuTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([sku, units]) => ({ name: sku.length > 14 ? sku.slice(0, 14) : sku, units }));

  const flagged = exceptions.filter((e: any) => e.stock_risk_flag || e.override_flag);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>
  );

  return (
    <div className="p-6 space-y-6 pb-20 lg:pb-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Current State</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          Bottoms-up demand plan — {filters.version_id || "LATEST_EST"} FY{filters.fiscal_year || 2024}
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Forecast Units" value={fmt(totalUnits)} />
        <KpiCard label="Total Forecast $" value={fmtDollar(totalDollars)} />
        <KpiCard
          label="vs Budget"
          value={fmtPct(vsBudget)}
          color={vsBudget !== null ? (vsBudget >= 0 ? "text-success" : "text-danger") : ""}
        />
        <KpiCard
          label="vs Prior Year"
          value={fmtPct(vsPY)}
          color={vsPY !== null ? (vsPY >= 0 ? "text-success" : "text-danger") : ""}
        />
      </div>

      {/* Monthly trend */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Monthly Trend — Sell-In Units</h2>
        <LineCompareChart
          data={trendData}
          lines={[
            { key: "This Year", color: "#6366F1", label: "This Year" },
            { key: "Prior Year", color: "#94A3B8", label: "Prior Year" },
          ]}
        />
      </div>

      {/* SKU × Retailer heatmap */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">SKU × Retailer Matrix (Top 15 SKUs)</h2>
        <HeatmapTable rows={top15Skus} cols={accounts} data={heatData} rowLabel="SKU" />
      </div>

      {/* Top 10 SKUs */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Top 10 SKUs by Forecast Units</h2>
        <BarStackChart
          data={top10}
          bars={[{ key: "units", color: "#6366F1", label: "Forecast Units" }]}
          xKey="name"
        />
      </div>

      {/* Exception flags */}
      {flagged.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Exception Flags ({flagged.length})
          </h2>
          <div className="space-y-2 max-h-64 overflow-auto">
            {flagged.slice(0, 20).map((e: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-text-primary text-sm font-medium">{e.sku_id}</span>
                <ExceptionBadge
                  stockRisk={!!e.stock_risk_flag}
                  overrideFlag={!!e.override_flag}
                  isNewSku={!!e.is_new_sku}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
