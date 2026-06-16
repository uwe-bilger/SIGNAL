from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/pos", tags=["pos"])


@router.get("/weekly")
def pos_weekly(
    fiscal_year:        int,
    sku_id:             Optional[str] = None,
    key_account_id:     Optional[str] = None,
    fiscal_week_start:  Optional[int] = None,
    fiscal_week_end:    Optional[int] = None,
):
    parts = [f"p.fiscal_year = {fiscal_year}"]
    if sku_id:            parts.append(f"p.sku_id = '{sku_id}'")
    if key_account_id:    parts.append(f"p.key_account_id = '{key_account_id}'")
    if fiscal_week_start: parts.append(f"p.fiscal_week >= {fiscal_week_start}")
    if fiscal_week_end:   parts.append(f"p.fiscal_week <= {fiscal_week_end}")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT p.sku_id, p.key_account_id, p.date_id, p.fiscal_year,
               p.fiscal_week, p.pos_units, p.pos_dollars,
               p.inventory_on_hand_units, p.weeks_of_supply
        FROM {q('fact_pos_weekly')} p
        {where}
        ORDER BY p.date_id
        LIMIT 2000
    """
    return run_query(sql)


@router.get("/monthly")
def pos_monthly(
    fiscal_year:    int,
    sku_id:         Optional[str] = None,
    key_account_id: Optional[str] = None,
):
    parts = [f"t.calendar_year = {fiscal_year}"]
    if sku_id:         parts.append(f"p.sku_id = '{sku_id}'")
    if key_account_id: parts.append(f"p.key_account_id = '{key_account_id}'")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            p.sku_id, p.key_account_id,
            t.calendar_month, t.calendar_month_name,
            SUM(p.pos_units * CAST(t.partial_week_proration_factor AS FLOAT64))   AS pos_units,
            SUM(p.pos_dollars * CAST(t.partial_week_proration_factor AS FLOAT64)) AS pos_dollars,
            AVG(p.inventory_on_hand_units) AS avg_inventory,
            AVG(p.weeks_of_supply)         AS avg_wos
        FROM {q('fact_pos_weekly')} p
        JOIN {q('dim_time')} t ON p.date_id = CAST(t.date_id AS DATE)
        {where}
        GROUP BY 1,2,3,4
        ORDER BY t.calendar_month
        LIMIT 2000
    """
    return run_query(sql)
