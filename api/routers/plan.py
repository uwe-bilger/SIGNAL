from fastapi import APIRouter, Query
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/plan", tags=["plan"])


def _where_clauses(
    division: Optional[str], brand: Optional[str], category: Optional[str],
    channel_type: Optional[str], key_account: Optional[str],
    fiscal_year: Optional[int], version_id: Optional[str],
) -> str:
    parts = []
    if division:     parts.append(f"s.division_id = '{division}'")
    if brand:        parts.append(f"s.brand_id = '{brand}'")
    if category:     parts.append(f"s.category_id = '{category}'")
    if channel_type: parts.append(f"ka.channel_type_id = '{channel_type}'")
    if key_account:  parts.append(f"f.key_account_id = '{key_account}'")
    if fiscal_year:  parts.append(f"f.fiscal_year = {fiscal_year}")
    if version_id:   parts.append(f"f.version_id = '{version_id}'")
    return ("WHERE " + " AND ".join(parts)) if parts else ""


@router.get("/summary")
def plan_summary(
    division:     Optional[str] = None,
    brand:        Optional[str] = None,
    category:     Optional[str] = None,
    channel_type: Optional[str] = None,
    key_account:  Optional[str] = None,
    fiscal_year:  Optional[int] = None,
    version_id:   Optional[str] = Query(default=None),
):
    where = _where_clauses(division, brand, category, channel_type, key_account, fiscal_year, version_id)
    sql = f"""
        SELECT
            f.fiscal_year, f.fiscal_month, f.version_id,
            s.division_id, s.brand_id, s.category_id,
            SUM(f.sell_in_units)          AS sell_in_units,
            SUM(f.sell_in_dollars)        AS sell_in_dollars,
            SUM(f.total_forecast_units)   AS total_forecast_units,
            SUM(f.total_forecast_dollars) AS total_forecast_dollars,
            SUM(f.inventory_on_hand_units)AS inventory_on_hand_units
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
        JOIN {q('dim_key_account')} ka ON f.key_account_id = ka.key_account_id
        {where}
        GROUP BY 1,2,3,4,5,6
        ORDER BY f.fiscal_year, f.fiscal_month, f.version_id
        LIMIT 5000
    """
    return run_query(sql)


@router.get("/sku-detail")
def sku_detail(
    sku_id:        str,
    key_account_id:Optional[str] = None,
    fiscal_year:   Optional[int] = None,
    version_id:    Optional[str] = None,
):
    parts = [f"f.sku_id = '{sku_id}'"]
    if key_account_id: parts.append(f"f.key_account_id = '{key_account_id}'")
    if fiscal_year:    parts.append(f"f.fiscal_year = {fiscal_year}")
    if version_id:     parts.append(f"f.version_id = '{version_id}'")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            f.fiscal_year, f.fiscal_month, f.version_id,
            f.sku_id, f.key_account_id,
            f.sell_in_units, f.sell_in_dollars,
            f.stat_forecast_units, f.manual_override_units,
            f.promo_uplift_units, f.total_forecast_units,
            f.total_forecast_dollars, f.inventory_on_hand_units,
            f.weeks_of_supply
        FROM {q('fact_financial_plan')} f
        {where}
        ORDER BY f.fiscal_year, f.fiscal_month, f.version_id
    """
    return run_query(sql)


@router.get("/version-compare")
def version_compare(
    version_a:    str,
    version_b:    str,
    fiscal_year:  int,
    division:     Optional[str] = None,
):
    div_filter = f"AND s.division_id = '{division}'" if division else ""
    sql = f"""
        WITH base AS (
            SELECT
                f.fiscal_month,
                f.version_id,
                SUM(f.total_forecast_units)   AS forecast_units,
                SUM(f.total_forecast_dollars) AS forecast_dollars
            FROM {q('fact_financial_plan')} f
            JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
            WHERE f.fiscal_year = {fiscal_year}
              AND f.version_id IN ('{version_a}', '{version_b}')
              {div_filter}
            GROUP BY 1,2
        )
        SELECT
            a.fiscal_month,
            a.forecast_units AS version_a_units,
            b.forecast_units AS version_b_units,
            b.forecast_units - a.forecast_units AS delta_units,
            SAFE_DIVIDE(b.forecast_units - a.forecast_units, a.forecast_units) AS delta_pct,
            a.forecast_dollars AS version_a_dollars,
            b.forecast_dollars AS version_b_dollars
        FROM base a
        JOIN base b USING (fiscal_month)
        WHERE a.version_id = '{version_a}'
          AND b.version_id = '{version_b}'
        ORDER BY fiscal_month
    """
    return run_query(sql)
