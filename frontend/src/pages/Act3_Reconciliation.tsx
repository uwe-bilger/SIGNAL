import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";
import { WaterfallChart } from "../components/Charts/WaterfallChart";
import { LineCompareChart } from "../components/Charts/LineCompareChart";
import { BarStackChart } from "../components/Charts/BarStackChart";

interface Props { filters: Filters }

const VERSION_COLORS = ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#94A3B8"];
const LE_VERSIONS = ["BUDGET", "OP_PLAN", "LE1", "LE2", "LE3", "LATEST_EST"];

export function Act3_Reconciliation({ filters }: Props) {
  const [reconcData, setReconcData] = useState<any>(null);
  const [accuracy, setAccuracy] = useState<any[]>([]);
  const [lagData, setLagData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fy = filters.fiscal_year || 2024;
    const params: any = { fiscal_year: fy };
    if (filters.division) params.division = filters.division;

    Promise.all([
      api.get("/api/reconciliation/summary", { params }),
      api.get("/api/forecast/accuracy", { params }),
      api.get("/api/forecast/lag-compare", { params: { fiscal_year: fy } }),
    ]).then(([recR, accR, lagR]) => {
      setReconcData(recR.data);
      setAccuracy(accR.data || []);
      setLagData(lagR.data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.division]);

  const waterfall = reconcData?.waterfall || [];
  const monthly = reconcData?.monthly_by_version || [];

  // Build LE version lines from monthly data
  const leByVersion: Record<string, Record<number, number>> = {};
  monthly.forEach((r: any) => {
    if (!leByVersion[r.version_id]) leByVersion[r.version_id] = {};
    leByVersion[r.version_id][r.fiscal_month] = r.forecast_units || 0;
  });
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const leChartData = months.map(m => {
    const entry: any = { name: `M${m}` };
    LE_VERSIONS.forEach(v => { entry[v] = leByVersion[v]?.[m] || 0; });
    return entry;
  });

  // Lag accuracy bar chart
  const lagChartData = lagData.map((r: any) => ({
    name: r.lag_label || r.lag_version_id,
    MAPE: r.avg_mape ? (r.avg_mape * 100).toFixed(1) : 0,
  }));

  // Bias analysis by division
  const biasData = accuracy.map((r: any) => ({
    name: r.division_id,
    "Mean Error": r.mean_error ? (r.mean_error * 100).toFixed(1) : 0,
  }));

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>
  );

  return (
    <div className="p-6 space-y-6 pb-20 lg:pb-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Reconciliation</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          Plan vs LE vs Budget — FY{filters.fiscal_year || 2024}
        </p>
      </div>

      {/* Version waterfall */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-1">Version Comparison Waterfall</h2>
        <p className="text-text-secondary text-xs mb-4">
          Budget → OP Plan → LE1 → LE2 → LE3 → Latest Est
        </p>
        <WaterfallChart data={waterfall} />
        {waterfall.length > 0 && (
          <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 mt-4">
            {waterfall.map((w: any) => (
              <div key={w.version_id} className="text-center">
                <div className="text-text-secondary text-xs">{w.version_id.replace("_", " ")}</div>
                <div className="text-text-primary font-semibold text-sm">
                  {w.total_units >= 1_000_000
                    ? (w.total_units / 1_000_000).toFixed(1) + "M"
                    : (w.total_units / 1_000).toFixed(0) + "K"}
                </div>
                <div className={`text-xs ${w.delta_units >= 0 ? "text-success" : "text-danger"}`}>
                  {w.delta_units === 0 ? "—" : (w.delta_units >= 0 ? "+" : "") + (w.delta_units / 1_000).toFixed(0) + "K"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LE versions over time */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Plan Versions Over Time</h2>
        <LineCompareChart
          data={leChartData}
          lines={LE_VERSIONS.map((v, i) => ({ key: v, color: VERSION_COLORS[i], label: v.replace("_", " ") }))}
          xKey="name"
        />
      </div>

      {/* Lag accuracy */}
      {lagChartData.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-1">Lag Accuracy (MAPE%)</h2>
          <p className="text-text-secondary text-xs mb-4">
            Lower is better. Benchmark: 10% (dashed line). LAG1 = 1 month out, LAG10 = 10 months out.
          </p>
          <BarStackChart
            data={lagChartData}
            bars={[{ key: "MAPE", color: "#6366F1", label: "MAPE %" }]}
            xKey="name"
          />
        </div>
      )}

      {/* Bias analysis */}
      {biasData.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-1">Forecast Bias by Division</h2>
          <p className="text-text-secondary text-xs mb-4">
            Positive = over-forecasting. Negative = under-forecasting.
          </p>
          <BarStackChart
            data={biasData}
            bars={[{ key: "Mean Error", color: "#F59E0B", label: "Mean Error %" }]}
            xKey="name"
          />
        </div>
      )}
    </div>
  );
}
