from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/accuracy")
def forecast_accuracy(
    fiscal_year: int,
    division:    Optional[str] = None,
    lag_versions: Optional[str] = None,   # comma-separated e.g. "LAG1,LAG3,LAG6"
):
    parts = [f"fs.fiscal_year = {fiscal_year}"]
    if division:     parts.append(f"s.division_id = '{division}'")
    if lag_versions:
        lags = [f"'{v.strip()}'" for v in lag_versions.split(",")]
        parts.append(f"fs.version_id IN ({', '.join(lags)})")
    else:
        parts.append("v.version_type = 'ForecastAccuracy'")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            fs.version_id,
            CAST(v.lag_months AS INT64)                       AS lag_months,
            COUNT(*)                                          AS snapshots,
            AVG(ABS(fs.forecast_error_pct))                   AS mape,
            AVG(fs.forecast_error_pct)                        AS mean_bias,
            SUM(fs.actual_units)                              AS total_actual_units
        FROM {q('fact_forecast_snapshot')} fs
        JOIN {q('dim_version')} v ON fs.version_id = v.version_id
        JOIN {q('dim_sku')} s     ON fs.sku_id = s.sku_id
        {where}
          AND fs.actual_units IS NOT NULL
          AND fs.actual_units > 0
          AND fs.forecast_error_pct IS NOT NULL
        GROUP BY 1,2
        ORDER BY lag_months
    """
    return run_query(sql)


@router.get("/lag-compare")
def lag_compare(
    sku_id:       str,
    fiscal_year:  int,
    fiscal_month: int,
):
    sql = f"""
        SELECT
            fs.version_id,
            CAST(v.lag_months AS INT64) AS lag_months,
            fs.snapshot_date,
            fs.forecast_units,
            fs.actual_units,
            fs.forecast_error_units,
            fs.forecast_error_pct
        FROM {q('fact_forecast_snapshot')} fs
        JOIN {q('dim_version')} v ON fs.version_id = v.version_id
        WHERE fs.sku_id = '{sku_id}'
          AND fs.fiscal_year = {fiscal_year}
          AND fs.fiscal_month = {fiscal_month}
          AND v.version_type = 'ForecastAccuracy'
        ORDER BY v.lag_months DESC
    """
    return run_query(sql)
