from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])

FINANCIAL_VERSIONS = ["BUDGET", "OP_PLAN", "LE1", "LE2", "LE3", "LATEST_EST"]


@router.get("/summary")
def reconciliation_summary(
    fiscal_year: int,
    division:    Optional[str] = None,
):
    div_filter = f"AND s.division_id = '{division}'" if division else ""
    versions_str = ", ".join(f"'{v}'" for v in FINANCIAL_VERSIONS)
    sql = f"""
        SELECT
            f.version_id,
            v.version_order,
            f.fiscal_month,
            SUM(f.total_forecast_units)   AS forecast_units,
            SUM(f.total_forecast_dollars) AS forecast_dollars,
            SUM(f.sell_in_units)          AS sell_in_units
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_version')} v ON f.version_id = v.version_id
        JOIN {q('dim_sku')} s     ON f.sku_id = s.sku_id
        WHERE f.fiscal_year = {fiscal_year}
          AND f.version_id IN ({versions_str})
          {div_filter}
        GROUP BY 1,2,3
        ORDER BY v.version_order, f.fiscal_month
    """
    rows = run_query(sql)

    # Build waterfall: delta between consecutive versions (annual totals)
    annual = {}
    for row in rows:
        vid = row["version_id"]
        annual[vid] = annual.get(vid, 0) + (row["forecast_units"] or 0)

    waterfall = []
    prev_units = None
    for vid in FINANCIAL_VERSIONS:
        if vid in annual:
            units = annual[vid]
            delta = units - prev_units if prev_units is not None else 0
            waterfall.append({"version_id": vid, "total_units": units, "delta_units": delta})
            prev_units = units

    return {"monthly_by_version": rows, "waterfall": waterfall}
