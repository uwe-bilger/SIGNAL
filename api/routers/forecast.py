from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

# TASK_09: forecast vs actuals is joined at QUERY TIME in v_forecast_accuracy.
# lag_months and version are derived there (from snapshot_date vs
# target_period_date), never stored.


@router.get("/accuracy")
def forecast_accuracy(
    fiscal_year: int,
    division:    Optional[str] = None,
    max_lag:     int = 12,
):
    div_filter = f"AND s.division_id = '{division}'" if division else ""
    sql = f"""
        SELECT
            fa.lag_months,
            COUNT(*)                 AS snapshots,
            AVG(ABS(fa.error_pct))   AS mape,
            AVG(fa.error_pct)        AS mean_bias,
            SUM(fa.actual_units)     AS total_actual_units,
            1 - AVG(ABS(fa.error_pct)) AS wfa_estimate
        FROM {q('v_forecast_accuracy')} fa
        JOIN {q('dim_sku')} s USING (sku_id)
        WHERE fa.fiscal_year = {int(fiscal_year)}
          AND fa.lag_months <= {int(max_lag)}
          {div_filter}
        GROUP BY 1
        ORDER BY fa.lag_months
    """
    return run_query(sql)


@router.get("/accuracy-by-division")
def accuracy_by_division(
    fiscal_year: int,
    max_lag:     int = 3,
):
    """Short-lag bias by business line — feeds the bias chart."""
    sql = f"""
        SELECT
            s.division_id,
            COUNT(*)               AS snapshots,
            AVG(ABS(fa.error_pct)) AS mape,
            AVG(fa.error_pct)      AS mean_bias
        FROM {q('v_forecast_accuracy')} fa
        JOIN {q('dim_sku')} s USING (sku_id)
        WHERE fa.fiscal_year = {int(fiscal_year)}
          AND fa.lag_months <= {int(max_lag)}
        GROUP BY 1
        ORDER BY 1
    """
    return run_query(sql)


@router.get("/lag-compare")
def lag_compare(
    fiscal_year:  int,
    sku_id:       Optional[str] = None,
    fiscal_month: Optional[int] = None,
):
    """MAPE by lag — optionally narrowed to one SKU / target month."""
    parts = [f"fa.fiscal_year = {int(fiscal_year)}"]
    if sku_id:       parts.append(f"fa.sku_id = '{sku_id}'")
    if fiscal_month: parts.append(f"fa.fiscal_month = {int(fiscal_month)}")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            fa.lag_months,
            FORMAT('Lag %d', fa.lag_months) AS lag_label,
            COUNT(*)                        AS snapshots,
            AVG(ABS(fa.error_pct))          AS avg_mape,
            AVG(fa.error_pct)               AS avg_bias,
            SUM(fa.forecast_units)          AS forecast_units,
            SUM(fa.actual_units)            AS actual_units
        FROM {q('v_forecast_accuracy')} fa
        {where}
        GROUP BY 1, 2
        ORDER BY fa.lag_months
    """
    return run_query(sql)
