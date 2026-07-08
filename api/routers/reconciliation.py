from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])

# TASK_09: versions are derived labels (Budget, LE01..LE11 — no LE12).
# An LE snapshot only forecasts the REMAINING months of its year, so annual
# totals are made comparable the FP&A way: YTD actuals + remaining forecast.
VERSION_ORDER = ["Budget"] + [f"LE{i:02d}" for i in range(1, 12)]


def _snapshot_month(version_id: str) -> int:
    """Snapshot calendar month within the target year (Budget = Dec prior = 0)."""
    return 0 if version_id == "Budget" else int(version_id[2:])


@router.get("/summary")
def reconciliation_summary(
    fiscal_year: int,
    division:    Optional[str] = None,
):
    div_fc  = f"AND s.division_id = '{division}'" if division else ""
    div_act = div_fc

    monthly = run_query(f"""
        SELECT
            f.version   AS version_id,
            f.fiscal_month,
            SUM(f.forecast_units)                                 AS forecast_units,
            SUM(f.forecast_units * CAST(s.unit_price AS FLOAT64)) AS forecast_dollars
        FROM {q('v_forecast_sellin')} f
        JOIN {q('dim_sku')} s USING (sku_id)
        WHERE f.fiscal_year = {int(fiscal_year)}
          {div_fc}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)

    actuals = run_query(f"""
        SELECT
            EXTRACT(MONTH FROM a.period_date) AS fiscal_month,
            SUM(a.actual_units)               AS actual_units
        FROM {q('fact_sellin_actuals')} a
        JOIN {q('dim_sku')} s USING (sku_id)
        WHERE EXTRACT(YEAR FROM a.period_date) = {int(fiscal_year)}
          {div_act}
        GROUP BY 1
    """)
    act_by_month = {int(r["fiscal_month"]): (r["actual_units"] or 0) for r in actuals}

    # forecast[version][month]
    fc: dict = {}
    for r in monthly:
        fc.setdefault(r["version_id"], {})[int(r["fiscal_month"])] = r["forecast_units"] or 0

    # Comparable annual total per version: actuals for elapsed months
    # (months <= snapshot month) + forecast for the remaining months.
    waterfall = []
    prev_units = None
    for vid in VERSION_ORDER:
        if vid not in fc:
            continue
        snap_m = _snapshot_month(vid)
        total = sum(act_by_month.get(m, 0) for m in range(1, snap_m + 1)) + \
                sum(v for m, v in fc[vid].items() if m > snap_m)
        delta = total - prev_units if prev_units is not None else 0
        waterfall.append({"version_id": vid, "total_units": total, "delta_units": delta})
        prev_units = total

    # Add version_order for chart sorting
    for r in monthly:
        r["version_order"] = VERSION_ORDER.index(r["version_id"]) if r["version_id"] in VERSION_ORDER else 99

    return {
        "monthly_by_version": monthly,
        "actuals_by_month":   [{"fiscal_month": m, "actual_units": u}
                               for m, u in sorted(act_by_month.items())],
        "waterfall":          waterfall,
    }
