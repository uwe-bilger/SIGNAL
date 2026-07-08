import React, { useEffect, useState } from "react";
import api from "../api/client";
import { Filters } from "../hooks/usePlan";

interface Props { filters: Filters }

function fmt(n: number) {
  if (!n && n !== 0) return "—";
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(Math.round(n));
}

function fmtPct(n: number) {
  if (!n && n !== 0) return "—";
  return (n * 100).toFixed(1) + "%";
}

const STATUS_COLOR: Record<string, string> = {
  live_on_target: "#10B981",
  in_flight:      "#F59E0B",
  legacy:         "#EF4444",
};

const STATUS_LABEL: Record<string, string> = {
  live_on_target: "Live on JDE",
  in_flight:      "Migration In-Flight",
  legacy:         "Legacy SAP",
};

export function Act4Integration({ filters }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/api/integration/overview")
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>
  );

  const sites: any[]            = data?.sites             || [];
  const dqTrend: any[]          = data?.dq_trend           || [];
  const acqSummary: any[]       = data?.acquisition_summary || [];
  const newSkus: any[]          = data?.new_skus            || [];
  const wfaTrend: any[]         = data?.wfa_trend           || [];
  const newSkuRisk: any[]       = data?.new_sku_risk         || [];

  const realSites = sites.filter((s: any) => s.is_placeholder_site === "False" || s.is_placeholder_site === false);
  const liveCount = realSites.filter((s: any) => s.migration_status === "live_on_target").length;

  // Average WFA for most recent year from trend data
  const wfa2024 = wfaTrend.filter((r: any) => r.fiscal_year === 2024 || r.fiscal_year === "2024");
  const avgWfa  = wfa2024.length
    ? wfa2024.reduce((a: number, r: any) => a + (Number(r.wfa_estimate) || 0), 0) / wfa2024.length
    : 0.54;

  // Average data quality by site
  const siteAvgDq: Record<string, number> = {};
  dqTrend.forEach((r: any) => {
    if (!siteAvgDq[r.site_id]) siteAvgDq[r.site_id] = 0;
    siteAvgDq[r.site_id] = (siteAvgDq[r.site_id] + Number(r.avg_data_quality)) / 2;
  });

  // WFA by year (average across all divisions and months)
  const wfaByYear: Record<string, number[]> = {};
  wfaTrend.forEach((r: any) => {
    const yr = String(r.fiscal_year);
    if (!wfaByYear[yr]) wfaByYear[yr] = [];
    const v = Number(r.wfa_estimate);
    if (!isNaN(v) && v > 0 && v < 1) wfaByYear[yr].push(v);
  });
  const wfaYearPoints = Object.entries(wfaByYear)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([yr, vals]) => ({
      year: yr,
      wfa: vals.reduce((a, b) => a + b, 0) / vals.length,
    }));

  const wfaMin = 0.40;
  const wfaMax = 0.85;

  const skuRiskMap: Record<string, { units: number; channels: number; dq: number }> = {};
  newSkuRisk.forEach((r: any) => {
    if (!skuRiskMap[r.sku_id]) skuRiskMap[r.sku_id] = { units: 0, channels: 0, dq: 0 };
    skuRiskMap[r.sku_id].units    += Number(r.forecast_units) || 0;
    skuRiskMap[r.sku_id].channels  = Number(r.channel_count) || 0;
    skuRiskMap[r.sku_id].dq        = Number(r.avg_dq_score) || 0;
  });
  const riskySKUs = Object.entries(skuRiskMap)
    .filter(([, v]) => v.units < 200 || v.channels < 2)
    .slice(0, 9);

  return (
    <div className="p-6 space-y-6 pb-20 lg:pb-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">FSD Integration</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          Acquisition boundary · ERP migration waves · Data quality transition
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">Sites Live on JDE</div>
          <div className="text-2xl font-bold text-success">{liveCount} / {realSites.length}</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">WFA Baseline</div>
          <div className="text-2xl font-bold text-warning">{fmtPct(avgWfa)}</div>
          <div className="text-text-secondary text-xs mt-1">Target 75%</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">New SKUs (Post-TF)</div>
          <div className="text-2xl font-bold text-primary">{newSkus.length}</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="text-text-secondary text-xs uppercase tracking-wider mb-2">Acquisition Close</div>
          <div className="text-2xl font-bold text-text-primary">Sep '25</div>
          <div className="text-text-secondary text-xs mt-1">From Solventum</div>
        </div>
      </div>

      {/* ERP migration timeline by site */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-1">ERP Migration — Site-by-Site Waves</h2>
        <p className="text-text-secondary text-xs mb-4">
          Legacy SAP (3M/Solventum) → Oracle JD Edwards. Each cutover creates a dateable
          data-quality step change — a real level shift, not a forecast artifact.
        </p>
        <div className="space-y-3">
          {sites.map((site: any, i: number) => {
            const color  = STATUS_COLOR[site.migration_status] || "#94A3B8";
            const label  = STATUS_LABEL[site.migration_status] || site.migration_status;
            const isPlaceholder = site.is_placeholder_site === "True" || site.is_placeholder_site === true;
            const dq = siteAvgDq[site.site_id];
            return (
              <div key={i} className="flex items-center gap-4">
                <div className="w-48 flex-shrink-0">
                  <div className="text-text-primary text-sm font-medium flex items-center gap-1">
                    {site.city}, {site.country}
                    {isPlaceholder && (
                      <span className="text-xs text-text-secondary italic ml-1">(illustrative)</span>
                    )}
                  </div>
                  <div className="text-text-secondary text-xs">Wave {site.migration_wave} · Cutover {site.planned_cutover_date}</div>
                </div>
                <div className="flex-1 flex items-center gap-3">
                  <span
                    className="px-2 py-0.5 rounded text-xs font-medium"
                    style={{ backgroundColor: color + "22", color }}
                  >
                    {label}
                  </span>
                  {dq !== undefined && (
                    <div className="flex items-center gap-2 flex-1">
                      <div className="text-text-secondary text-xs w-16">DQ score</div>
                      <div className="flex-1 h-2 bg-border/40 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(dq || 0.5) * 100}%`,
                            backgroundColor: dq > 0.85 ? "#10B981" : dq > 0.65 ? "#F59E0B" : "#EF4444",
                          }}
                        />
                      </div>
                      <div className="text-text-secondary text-xs w-10 text-right">
                        {dq ? (dq * 100).toFixed(0) + "%" : "—"}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* WFA trend chart (simplified sparkline) */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-1">
          WFA Trend — Weighted Forecast Accuracy
        </h2>
        <p className="text-text-secondary text-xs mb-4">
          54% baseline at acquisition → 75% target within 12 months.
          Noisy improving trend — routine variation around a genuine step-change
          (a process behavior chart teaching example).
        </p>
        <div className="flex items-end gap-1 h-24">
          {wfaYearPoints.map((pt, i) => {
            const pct    = Math.max(0, Math.min(1, (pt.wfa - wfaMin) / (wfaMax - wfaMin)));
            const height = Math.round(pct * 80) + 4;
            const color  = pt.wfa >= 0.72 ? "#10B981" : pt.wfa >= 0.60 ? "#F59E0B" : "#EF4444";
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="text-text-secondary text-xs">{fmtPct(pt.wfa)}</div>
                <div className="w-full rounded-t" style={{ height, backgroundColor: color + "99", border: `1px solid ${color}` }} />
                <div className="text-text-secondary text-xs">{pt.year}</div>
              </div>
            );
          })}
          {/* Target line label */}
          <div className="self-center ml-2 text-success text-xs whitespace-nowrap">← 75% target</div>
        </div>
      </div>

      {/* Acquisition boundary: pre vs post summary */}
      {acqSummary.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Acquisition Boundary — Pre vs. Post Sept 2025
          </h2>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-3">Period</th>
                  <th className="text-left py-2 px-3">Business Line</th>
                  <th className="text-right py-2 px-3">SKUs</th>
                  <th className="text-right py-2 px-3">Total Units</th>
                  <th className="text-right py-2 px-3">Revenue</th>
                  <th className="text-right py-2 px-3">Avg DQ Score</th>
                </tr>
              </thead>
              <tbody>
                {acqSummary.map((r: any, i: number) => {
                  const isPost = r.is_pre_acquisition === "False" || r.is_pre_acquisition === false;
                  const dq = Number(r.avg_data_quality);
                  return (
                    <tr key={i} className="border-b border-border hover:bg-white/5">
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          isPost ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                        }`}>
                          {isPost ? "Post-Acquisition" : "Pre-Acquisition"}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-text-secondary">{r.division_id}</td>
                      <td className="py-2 px-3 text-right text-text-primary">{fmt(r.sku_count)}</td>
                      <td className="py-2 px-3 text-right text-text-primary">{fmt(r.total_units)}</td>
                      <td className="py-2 px-3 text-right text-text-primary">
                        ${fmt(r.total_dollars)}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className={dq > 0.80 ? "text-success" : dq > 0.65 ? "text-warning" : "text-danger"}>
                          {(dq * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Post-acquisition new SKU list */}
      {newSkus.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-1">
            New Products — Post-TF Acquisition
          </h2>
          <p className="text-text-secondary text-xs mb-4">
            SKUs introduced after TF closed the acquisition (Sept 2025), enabled by
            Thermo Fisher R&D resources. No Solventum-era history — qualification
            campaigns required.
          </p>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-3">SKU ID</th>
                  <th className="text-left py-2 px-3">Product</th>
                  <th className="text-left py-2 px-3">Business Line</th>
                  <th className="text-right py-2 px-3">Unit Price</th>
                  <th className="text-left py-2 px-3">Launch</th>
                </tr>
              </thead>
              <tbody>
                {newSkus.map((s: any, i: number) => (
                  <tr key={i} className="border-b border-border hover:bg-white/5">
                    <td className="py-2 px-3 text-primary font-mono text-xs">{s.sku_id}</td>
                    <td className="py-2 px-3 text-text-primary">{s.sku_name}</td>
                    <td className="py-2 px-3 text-text-secondary">{s.division_id}</td>
                    <td className="py-2 px-3 text-right text-text-secondary">${Number(s.unit_price).toFixed(0)}</td>
                    <td className="py-2 px-3 text-text-secondary text-xs">{s.launch_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Channel coverage risk for new SKUs (supply/inventory domain is a follow-up) */}
      {riskySKUs.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            New SKU Channel Coverage Risk ({riskySKUs.length})
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {riskySKUs.map(([skuId, v], i) => (
              <div key={i} className="border border-warning/20 bg-warning/5 rounded-lg p-4">
                <div className="text-warning font-medium text-sm mb-2">{skuId}</div>
                <div className="text-text-secondary text-xs space-y-1">
                  <div>Forecast: {fmt(v.units)} units</div>
                  <div>Channels: {v.channels}</div>
                  <div>DQ Score: {v.dq ? (v.dq * 100).toFixed(0) + "%" : "—"}</div>
                  <div className="text-warning mt-2 font-medium">⚠ Run qualification campaign</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
