from fastapi import APIRouter, Query
from typing import Optional
from db.bigquery_client import run_query, q

# TASK_09: finance's own plan at its own grain — Division × Channel ×
# Category, revenue/cost/margin only. No SKU, no units, anywhere. Plan vs
# actuals is compared at QUERY TIME, never stored pre-joined.
router = APIRouter(prefix="/api/financial", tags=["financial"])

VALID_VERSIONS = {"Budget"} | {f"LE{i:02d}" for i in range(1, 12)}


@router.get("/summary")
def financial_summary(
    fiscal_year:  int,
    division:     Optional[str] = None,
    channel_type: Optional[str] = None,
    version_id:   Optional[str] = Query(default=None),
):
    parts = [f"f.fiscal_year = {int(fiscal_year)}"]
    if division:     parts.append(f"f.division_id = '{division}'")
    if channel_type: parts.append(f"f.channel_type_id = '{channel_type}'")
    if version_id and version_id in VALID_VERSIONS:
        version_clause = f"AND f.version = '{version_id}'"
        latest_qualify = ""
    else:
        version_clause = ""
        latest_qualify = """
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY f.division_id, f.channel_type_id, f.category_id,
                             f.target_period_date
                ORDER BY f.snapshot_date DESC
            ) = 1
        """
    where = "WHERE " + " AND ".join(parts)

    sql = f"""
        WITH plan_base AS (
            SELECT f.* FROM {q('v_financial_snapshot')} f
            {where} {version_clause}
            {latest_qualify}
        ),
        plan AS (
            SELECT
                fiscal_year, fiscal_month,
                division_id, channel_type_id, category_id,
                ANY_VALUE(version) AS version_id,
                SUM(revenue) AS plan_revenue,
                SUM(cost)    AS plan_cost,
                SUM(margin)  AS plan_margin
            FROM plan_base
            GROUP BY 1, 2, 3, 4, 5
        ),
        act AS (
            SELECT
                EXTRACT(YEAR  FROM a.period_date) AS fiscal_year,
                EXTRACT(MONTH FROM a.period_date) AS fiscal_month,
                a.division_id, a.channel_type_id, a.category_id,
                SUM(a.revenue) AS actual_revenue,
                SUM(a.cost)    AS actual_cost,
                SUM(a.margin)  AS actual_margin
            FROM {q('fact_financial_actuals')} a
            WHERE EXTRACT(YEAR FROM a.period_date) = {int(fiscal_year)}
              {"AND a.division_id = '" + division + "'" if division else ""}
              {"AND a.channel_type_id = '" + channel_type + "'" if channel_type else ""}
            GROUP BY 1, 2, 3, 4, 5
        )
        SELECT
            fiscal_year, fiscal_month,
            division_id, channel_type_id, category_id,
            plan.version_id,
            plan.plan_revenue, plan.plan_cost, plan.plan_margin,
            act.actual_revenue, act.actual_cost, act.actual_margin
        FROM plan
        FULL OUTER JOIN act
        USING (fiscal_year, fiscal_month, division_id, channel_type_id, category_id)
        ORDER BY fiscal_year, fiscal_month, division_id
        LIMIT 5000
    """
    return run_query(sql)
