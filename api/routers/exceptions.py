from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


@router.get("")
def get_exceptions(
    fiscal_year:   int,
    fiscal_month:  Optional[int] = None,
    division:      Optional[str] = None,
):
    parts = [f"f.fiscal_year = {fiscal_year}"]
    if fiscal_month: parts.append(f"f.fiscal_month = {fiscal_month}")
    if division:     parts.append(f"s.division_id = '{division}'")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            f.sku_id, s.sku_name, s.division_id, f.fiscal_year, f.fiscal_month,
            s.is_new_sku,
            MAX(CASE WHEN f.weeks_of_supply < 4 THEN 1 ELSE 0 END)  AS stock_risk_flag,
            MAX(CASE WHEN ABS(f.total_forecast_units - f.stat_forecast_units)
                          / NULLIF(f.stat_forecast_units, 0) > 0.10 THEN 1 ELSE 0 END) AS override_flag,
            AVG(f.weeks_of_supply) AS avg_wos,
            SUM(f.total_forecast_units) AS total_forecast_units
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
        {where}
          AND f.version_id = 'LATEST_EST'
        GROUP BY 1,2,3,4,5,6
        HAVING stock_risk_flag = 1 OR override_flag = 1 OR s.is_new_sku = TRUE
        ORDER BY stock_risk_flag DESC, override_flag DESC
        LIMIT 500
    """
    return run_query(sql)
