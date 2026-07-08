from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

# TASK_09: retail-POS framing replaced by B2B sell-through (Distributor and
# OEM Contract channels only — Direct/CDMO have no intermediary layer, so
# they have no rows here). Monthly grain only; the old weekly endpoint is gone.
# Kept under /api/pos so existing clients keep a stable base path.
router = APIRouter(prefix="/api/pos", tags=["sellthrough"])


@router.get("/monthly")
def sellthrough_monthly(
    fiscal_year:  int,
    sku_id:       Optional[str] = None,
    channel_type: Optional[str] = None,
):
    parts = [f"v.calendar_year = {int(fiscal_year)}"]
    if sku_id:       parts.append(f"v.sku_id = '{sku_id}'")
    if channel_type: parts.append(f"v.channel_type_id = '{channel_type}'")
    where = "WHERE " + " AND ".join(parts)
    sql = f"""
        SELECT
            v.sku_id, v.channel_type_id,
            v.calendar_year, v.calendar_month,
            v.sellthrough_units,
            v.sellthrough_dollars
        FROM {q('v_sellthrough_monthly')} v
        {where}
        ORDER BY v.calendar_month, v.sku_id
        LIMIT 2000
    """
    return run_query(sql)


@router.get("/vs-sellin")
def sellthrough_vs_sellin(
    fiscal_year:  int,
    channel_type: Optional[str] = None,
):
    """Sell-in vs sell-through by month — compared at QUERY TIME, never stored."""
    ch_st = f"AND st.channel_type_id = '{channel_type}'" if channel_type else \
            "AND st.channel_type_id IN ('CHN-02', 'CHN-03')"
    ch_si = f"AND si.channel_type_id = '{channel_type}'" if channel_type else \
            "AND si.channel_type_id IN ('CHN-02', 'CHN-03')"
    sql = f"""
        WITH st AS (
            SELECT EXTRACT(MONTH FROM st.period_date) AS month,
                   SUM(st.actual_units) AS sellthrough_units
            FROM {q('fact_sellthrough_actuals')} st
            WHERE EXTRACT(YEAR FROM st.period_date) = {int(fiscal_year)} {ch_st}
            GROUP BY 1
        ),
        si AS (
            SELECT EXTRACT(MONTH FROM si.period_date) AS month,
                   SUM(si.actual_units) AS sellin_units
            FROM {q('fact_sellin_actuals')} si
            WHERE EXTRACT(YEAR FROM si.period_date) = {int(fiscal_year)} {ch_si}
            GROUP BY 1
        )
        SELECT month, si.sellin_units, st.sellthrough_units,
               si.sellin_units - st.sellthrough_units AS channel_inventory_delta
        FROM si FULL OUTER JOIN st USING (month)
        ORDER BY month
    """
    return run_query(sql)
