import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";
import { WaterfallChart } from "../components/Charts/WaterfallChart";
import { BarStackChart } from "../components/Charts/BarStackChart";
import { ExceptionBadge } from "../components/Badges/ExceptionBadge";

interface Props { filters: Filters }

function fmt(n: number) {
  if (!n && n !== 0) return "—";
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(Math.round(n));
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

    const excParams = { fiscal_year: fy, version_id: "LATEST_EST" };

    Promise.all([
      api.get("/api/reconciliation/summary", { params }),
      api.get("/api/exceptions", { params: excParams }),
      api.get("/api/plan/summary", { params: { ...params, version_id: "BUDGET" } }),
      api.get("/api/plan/summary", { params: { ...params, version_id: "LATEST_EST" } }),
    ]).then(([recR, excR, budR, leR]) => {
      setReconcData(recR.data);
      setExceptions(excR.data || []);
      // Division comparison: budget vs latest
      const budDivs: Record<string, number> = {};
      const leDivs: Record<string, number> = {};
      (budR.data?.by_division || []).forEach((r: any) => { budDivs[r.division_id] = r.forecast_units; });
      (leR.data?.by_division || []).forEach((r: any) => { leDivs[r.division_id] = r.forecast_units; });
      const divs = Array.from(new Set([...Object.keys(budDivs), ...Object.keys(leDivs)]));
      setDivisionData(divs.map(d => ({
        name: d,
        Budget: budDivs[d] || 0,
        "Latest Est": leDivs[d] || 0,
      })));
    }).catch(() => {}).finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.division]);

  const waterfall = reconcData?.waterfall || [];
  const overrides = exceptions.filter((e: any) => e.override_flag).sort(
    (a: any, b: any) => Math.abs(b.override_qty || 0) - Math.abs(a.override_qty || 0)
  );

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
        <p className="text-text-secondary text-xs mb-4">Delta between consecutive plan versions</p>
        <WaterfallChart data={waterfall} />
      </div>

      {/* Budget vs Latest Est by Division */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Budget vs Latest Est by Division</h2>
        <BarStackChart
          data={divisionData}
          bars={[
            { key: "Budget", color: "#94A3B8", label: "Budget" },
            { key: "Latest Est", color: "#6366F1", label: "Latest Est" },
          ]}
          xKey="name"
        />
      </div>

      {/* Override exceptions */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">
          Manual Overrides ({overrides.length})
        </h2>
        {overrides.length === 0 ? (
          <p className="text-text-secondary text-sm">No override flags in current filter.</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-3">SKU</th>
                  <th className="text-right py-2 px-3">Stat Forecast</th>
                  <th className="text-right py-2 px-3">Override Qty</th>
                  <th className="text-right py-2 px-3">Final Forecast</th>
                  <th className="py-2 px-3">Flags</th>
                </tr>
              </thead>
              <tbody>
                {overrides.slice(0, 20).map((e: any, i: number) => (
                  <tr key={i} className="border-b border-border hover:bg-white/5">
                    <td className="py-2 px-3 text-text-primary font-medium">{e.sku_id}</td>
                    <td className="py-2 px-3 text-right text-text-secondary">{fmt(e.stat_forecast_units)}</td>
                    <td className={`py-2 px-3 text-right font-medium ${(e.override_qty || 0) >= 0 ? "text-success" : "text-danger"}`}>
                      {(e.override_qty || 0) >= 0 ? "+" : ""}{fmt(e.override_qty)}
                    </td>
                    <td className="py-2 px-3 text-right text-text-primary">{fmt(e.forecast_units)}</td>
                    <td className="py-2 px-3">
                      <ExceptionBadge
                        stockRisk={e.stock_risk_flag}
                        overrideFlag={e.override_flag}
                        isNewSku={e.is_new_sku}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Forward risk */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Forward Exception Layer</h2>
        <p className="text-text-secondary text-xs mb-4">
          SKUs flagged for stock risk in next 3 months
        </p>
        {exceptions.filter((e: any) => e.stock_risk_flag).length === 0 ? (
          <p className="text-text-secondary text-sm">No stock risk flags in current filter.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {exceptions.filter((e: any) => e.stock_risk_flag).slice(0, 9).map((e: any, i: number) => (
              <div key={i} className="border border-danger/20 bg-danger/5 rounded-lg p-3">
                <div className="text-danger font-medium text-sm">{e.sku_id}</div>
                <div className="text-text-secondary text-xs mt-1">
                  WOS: {e.weeks_on_hand ?? "—"} | Accuracy: {e.forecast_accuracy_pct ? (e.forecast_accuracy_pct * 100).toFixed(0) + "%" : "—"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
