import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";
import { WaterfallChart } from "../components/Charts/WaterfallChart";
import { BarStackChart } from "../components/Charts/BarStackChart";
import { ExceptionBadge } from "../components/Badges/ExceptionBadge";

interface Props { filters: Filters }

function fmtPct(n: number | null | undefined) {
  if (n === undefined || n === null || isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v >= 0 ? "+" : "";
  return sign + (v * 100).toFixed(1) + "%";
}

function sumByDivision(rows: any[]): Record<string, number> {
  const out: Record<string, number> = {};
  rows.forEach((r: any) => {
    out[r.division_id] = (out[r.division_id] || 0) + (Number(r.total_forecast_units) || 0);
  });
  return out;
}

export function Act2Challenger({ filters }: Props) {
  const [reconcData, setReconcData] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [divisionData, setDivisionData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fy = filters.fiscal_year || 2024;
    const params: any = { fiscal_year: fy };
    if (filters.division) params.division = filters.division;

    Promise.all([
      api.get("/api/reconciliation/summary", { params }),
      api.get("/api/exceptions", { params }),
      api.get("/api/plan/summary", { params: { ...params, version_id: "Budget" } }),
      api.get("/api/plan/summary", { params }),   // no version -> latest estimate
    ]).then(([recR, excR, budR, leR]) => {
      setReconcData(recR.data);
      setExceptions(excR.data || []);
      // Division comparison: Budget vs latest estimate (aggregated client-side)
      const budDivs = sumByDivision(budR.data || []);
      const leDivs  = sumByDivision(leR.data || []);
      const divs = Array.from(new Set([...Object.keys(budDivs), ...Object.keys(leDivs)]));
      setDivisionData(divs.sort().map(d => ({
        name: d,
        Budget: budDivs[d] || 0,
        "Latest Est": leDivs[d] || 0,
      })));
    }).catch(() => {}).finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.division]);

  const waterfall = reconcData?.waterfall || [];
  // Biggest misses first: sort by |mean bias| of short-lag forecasts
  const misses = [...exceptions].sort(
    (a: any, b: any) => Math.abs(b.mean_bias || 0) - Math.abs(a.mean_bias || 0)
  );
  const lowAccuracy = exceptions.filter((e: any) => e.accuracy_flag);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>
  );

  return (
    <div className="p-6 space-y-6 pb-20 lg:pb-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Challenger Pack</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          Top-down gap analysis — FY{filters.fiscal_year || 2024}
        </p>
      </div>

      {/* Gap analysis waterfall */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-1">Version Waterfall</h2>
        <p className="text-text-secondary text-xs mb-4">
          Budget → LE cycles. Each total = YTD actuals + remaining-month forecast
          (versions derived from snapshot dates — nothing stored, nothing pre-merged)
        </p>
        <WaterfallChart data={waterfall} />
      </div>

      {/* Budget vs Latest Est by Division */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Budget vs Latest Est by Business Line</h2>
        <BarStackChart
          data={divisionData}
          bars={[
            { key: "Budget", color: "#94A3B8", label: "Budget" },
            { key: "Latest Est", color: "#6366F1", label: "Latest Est" },
          ]}
          xKey="name"
        />
      </div>

      {/* Largest forecast misses */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">
          Largest Forecast Misses ({misses.length})
        </h2>
        <p className="text-text-secondary text-xs mb-4">
          Short-lag (≤3 months) forecast vs actuals, compared at query time.
          Positive bias = under-forecast, negative = over-forecast.
        </p>
        {misses.length === 0 ? (
          <p className="text-text-secondary text-sm">No exception flags in current filter.</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-3">SKU</th>
                  <th className="text-left py-2 px-3">Business Line</th>
                  <th className="text-right py-2 px-3">Mean Bias</th>
                  <th className="text-right py-2 px-3">MAPE</th>
                  <th className="py-2 px-3">Flags</th>
                </tr>
              </thead>
              <tbody>
                {misses.slice(0, 20).map((e: any, i: number) => (
                  <tr key={i} className="border-b border-border hover:bg-white/5">
                    <td className="py-2 px-3 text-text-primary font-medium">{e.sku_id}</td>
                    <td className="py-2 px-3 text-text-secondary">{e.division_id}</td>
                    <td className={`py-2 px-3 text-right font-medium ${(e.mean_bias || 0) >= 0 ? "text-success" : "text-danger"}`}>
                      {fmtPct(e.mean_bias)}
                    </td>
                    <td className="py-2 px-3 text-right text-text-secondary">
                      {e.mape !== null && e.mape !== undefined ? (Number(e.mape) * 100).toFixed(0) + "%" : "—"}
                    </td>
                    <td className="py-2 px-3">
                      <ExceptionBadge
                        accuracyFlag={!!e.accuracy_flag}
                        biasFlag={!!e.bias_flag}
                        isNewSku={e.is_new_sku === "True" || e.is_new_sku === true}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Low-accuracy watchlist */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Low-Accuracy Watchlist</h2>
        <p className="text-text-secondary text-xs mb-4">
          SKUs whose short-lag MAPE exceeds 35% — challenge these plans first
        </p>
        {lowAccuracy.length === 0 ? (
          <p className="text-text-secondary text-sm">No low-accuracy flags in current filter.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {lowAccuracy.slice(0, 9).map((e: any, i: number) => (
              <div key={i} className="border border-danger/20 bg-danger/5 rounded-lg p-3">
                <div className="text-danger font-medium text-sm">{e.sku_id}</div>
                <div className="text-text-secondary text-xs mt-1">
                  MAPE: {e.mape !== null && e.mape !== undefined ? (Number(e.mape) * 100).toFixed(0) + "%" : "—"} |
                  Bias: {fmtPct(e.mean_bias)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
