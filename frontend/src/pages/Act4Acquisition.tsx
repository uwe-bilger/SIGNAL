import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";
import { ExceptionBadge } from "../components/Badges/ExceptionBadge";

interface Props { filters: Filters }

function fmt(n: number) {
  if (!n && n !== 0) return "—";
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(Math.round(n));
}

function fmtDollar(n: number) {
  if (!n) return "—";
  return "$" + n.toFixed(2);
}

export function Act4Acquisition({ filters }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.get("/api/acquisition/overview")
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>
  );

  const newSkus = data?.new_skus || [];
  const comparable = data?.comparable_skus || [];
  const riskFlags = data?.supply_risk || [];
  const newSkuCount = data?.new_sku_count || 0;

  const divisionIds = Array.from(new Set(newSkus.map((s: any) => s.division_id))) as string[];

  // Stocking recommendation: match by subcategory from comparable
  const subCatAvg: Record<string, number> = {};
  comparable.forEach((c: any) => {
    if (!subCatAvg[c.subcategory_id]) subCatAvg[c.subcategory_id] = c.avg_monthly_units;
  });

  // Supply risk: SKUs with zero or very low forecast
  const skuRiskMap: Record<string, { units: number; accounts: number }> = {};
  riskFlags.forEach((r: any) => {
    if (!skuRiskMap[r.sku_id]) skuRiskMap[r.sku_id] = { units: 0, accounts: 0 };
    skuRiskMap[r.sku_id].units += r.forecast_units || 0;
    skuRiskMap[r.sku_id].accounts = r.account_count || 0;
  });
  const risky = Object.entries(skuRiskMap)
    .filter(([, v]) => v.units < 500 || v.accounts < 3)
    .slice(0, 9);

  return (
    <div className="p-6 space-y-6 pb-20 lg:pb-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">M&A Integration</h1>
        <p className="text-text-secondary text-sm mt-0.5">Hugimals acquisition — new SKU planning</p>
      </div>

      {/* Overview card */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">New SKUs</div>
          <div className="text-2xl font-bold text-primary">{newSkuCount}</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">Divisions</div>
          <div className="text-2xl font-bold text-text-primary">{divisionIds.length}</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">At Risk</div>
          <div className="text-2xl font-bold text-danger">{risky.length}</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">Go-Live</div>
          <div className="text-2xl font-bold text-text-primary">Jul '24</div>
        </div>
      </div>

      {/* New SKU list */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">New SKU List</h2>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-secondary text-xs border-b border-border">
                <th className="text-left py-2 px-3">SKU ID</th>
                <th className="text-left py-2 px-3">Name</th>
                <th className="text-left py-2 px-3">Category</th>
                <th className="text-right py-2 px-3">Unit Price</th>
                <th className="text-right py-2 px-3">Stocking Rec</th>
                <th className="text-left py-2 px-3">Launch</th>
              </tr>
            </thead>
            <tbody>
              {newSkus.map((s: any, i: number) => {
                const rec = subCatAvg[s.subcategory_id];
                return (
                  <tr
                    key={i}
                    onClick={() => setSelectedSku(selectedSku === s.sku_id ? null : s.sku_id)}
                    className={`border-b border-border cursor-pointer transition-colors ${
                      selectedSku === s.sku_id ? "bg-primary/10" : "hover:bg-white/5"
                    }`}
                  >
                    <td className="py-2 px-3 text-primary font-mono text-xs">{s.sku_id}</td>
                    <td className="py-2 px-3 text-text-primary">{s.sku_name}</td>
                    <td className="py-2 px-3 text-text-secondary">{s.category_id}</td>
                    <td className="py-2 px-3 text-right text-text-secondary">{fmtDollar(s.unit_price)}</td>
                    <td className="py-2 px-3 text-right">
                      {rec ? (
                        <span className="text-warning font-medium">{fmt(rec)}/mo</span>
                      ) : (
                        <span className="text-text-secondary">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-text-secondary text-xs">{s.launch_date}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comparable SKUs */}
      {selectedSku && (
        <div className="bg-surface border border-primary/30 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Comparable Analysis — {selectedSku}
          </h2>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-3">SKU</th>
                  <th className="text-left py-2 px-3">Name</th>
                  <th className="text-left py-2 px-3">Subcategory</th>
                  <th className="text-right py-2 px-3">Avg Monthly Units</th>
                </tr>
              </thead>
              <tbody>
                {comparable
                  .filter((c: any) => {
                    const sel = newSkus.find((s: any) => s.sku_id === selectedSku);
                    return sel && c.subcategory_id === sel.subcategory_id;
                  })
                  .slice(0, 5)
                  .map((c: any, i: number) => (
                    <tr key={i} className="border-b border-border hover:bg-white/5">
                      <td className="py-2 px-3 text-text-secondary font-mono text-xs">{c.sku_id}</td>
                      <td className="py-2 px-3 text-text-primary">{c.sku_name}</td>
                      <td className="py-2 px-3 text-text-secondary">{c.subcategory_id}</td>
                      <td className="py-2 px-3 text-right text-success font-medium">{fmt(c.avg_monthly_units)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Supply risk flags */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">
          Supply Risk Flags ({risky.length})
        </h2>
        {risky.length === 0 ? (
          <p className="text-text-secondary text-sm">No supply risk flags detected.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {risky.map(([skuId, v], i) => (
              <div key={i} className="border border-danger/20 bg-danger/5 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-danger font-medium text-sm">{skuId}</span>
                  <ExceptionBadge isNewSku />
                </div>
                <div className="text-text-secondary text-xs space-y-1">
                  <div>Forecast: {fmt(v.units)} units</div>
                  <div>Accounts: {v.accounts}</div>
                  <div className="text-warning mt-2 font-medium">⚠ Review supplier onboarding</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Transition timeline */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Transition Timeline</h2>
        <div className="overflow-auto">
          <div className="min-w-[600px]">
            {[
              { phase: "SKU Onboarding", start: 0, duration: 2, color: "#6366F1" },
              { phase: "First PO Placed", start: 2, duration: 1, color: "#10B981" },
              { phase: "First Shipment", start: 3, duration: 1, color: "#F59E0B" },
              { phase: "First POS Data", start: 4, duration: 2, color: "#8B5CF6" },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 mb-3">
                <div className="text-text-secondary text-xs w-36 flex-shrink-0">{item.phase}</div>
                <div className="flex-1 h-7 bg-border/40 rounded relative">
                  <div
                    className="absolute h-full rounded flex items-center px-2"
                    style={{
                      left: `${(item.start / 6) * 100}%`,
                      width: `${(item.duration / 6) * 100}%`,
                      backgroundColor: item.color + "33",
                      border: `1px solid ${item.color}55`,
                    }}
                  >
                    <span className="text-xs" style={{ color: item.color }}>
                      M{item.start + 1}–M{item.start + item.duration}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            <div className="flex gap-3 mt-1 ml-[144px]">
              {["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map(m => (
                <div key={m} className="flex-1 text-center text-text-secondary text-xs">{m}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
