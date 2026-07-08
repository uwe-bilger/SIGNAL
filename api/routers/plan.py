from fastapi import APIRouter, Query
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/plan", tags=["plan"])

# TASK_09: demand plan reads the sell-in forecast snapshots (units only).
# Dollars are derived at QUERY TIME as units × dim_sku.unit_price — never
# stored on the demand tables. version_id is the DERIVED label (Budget /
# LE01..LE11); omitting it means "latest available snapshot per target month".

VALID_VERSIONS = {"Budget"} | {f"LE{i:02d}" for i in range(1, 12)}


def _version_filter(version_id: Optional[str]) -> str:
    """WHERE fragment for the derived version, or QUALIFY-latest when absent."""
    if version_id and version_id in VALID_VERSIONS:
        return f"WHERE f.version = '{version_id}'"
    # Latest estimate: most recent snapshot for each target month
    # (WHERE TRUE because BigQuery requires WHERE/GROUP BY/HAVING with QUALIFY)
    return """
        WHERE TRUE
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY f.sku_id, f.site_id, f.channel_type_id, f.target_period_date
            ORDER BY f.snapshot_date DESC
        ) = 1
    """


def _dim_clauses(division, brand, category, channel_type, fiscal_year, alias="x"):
    parts = []
    if division:     parts.append(f"s.division_id = '{division}'")
    if brand:        parts.append(f"s.brand_id = '{brand}'")
    if category:     parts.append(f"s.category_id = '{category}'")
    if channel_type: parts.append(f"{alias}.channel_type_id = '{channel_type}'")
    if fiscal_year:  parts.append(f"{alias}.fiscal_year = {int(fiscal_year)}")
    return ("WHERE " + " AND ".join(parts)) if parts else ""


@router.get("/summary")
def plan_summary(
    division:     Optional[str] = None,
    brand:        Optional[str] = None,
    category:     Optional[str] = None,
    channel_type: Optional[str] = None,
    fiscal_year:  Optional[int] = None,
    version_id:   Optional[str] = Query(default=None),
):
    fc_where  = _dim_clauses(division, brand, category, channel_type, fiscal_year, alias="fb")
    act_where = _dim_clauses(division, brand, category, channel_type, fiscal_year, alias="am")
    sql = f"""
        WITH fc_base AS (
            SELECT f.* FROM {q('v_forecast_sellin')} f
            {_version_filter(version_id)}
        ),
        fc AS (
            SELECT
                fb.fiscal_year, fb.fiscal_month,
                s.division_id, s.brand_id, s.category_id,
                ANY_VALUE(fb.version)                                   AS version_id,
                SUM(fb.forecast_units)                                  AS total_forecast_units,
                SUM(fb.forecast_units * CAST(s.unit_price AS FLOAT64))  AS total_forecast_dollars
            FROM fc_base fb
            JOIN {q('dim_sku')} s USING (sku_id)
            {fc_where}
            GROUP BY 1, 2, 3, 4, 5
        ),
        act_base AS (
            SELECT
                a.sku_id, a.channel_type_id, a.actual_units,
                EXTRACT(YEAR  FROM a.period_date) AS fiscal_year,
                EXTRACT(MONTH FROM a.period_date) AS fiscal_month
            FROM {q('fact_sellin_actuals')} a
        ),
        act AS (
            SELECT
                am.fiscal_year, am.fiscal_month,
                s.division_id, s.brand_id, s.category_id,
                SUM(am.actual_units)                                    AS sell_in_units,
                SUM(am.actual_units * CAST(s.unit_price AS FLOAT64))    AS sell_in_dollars
            FROM act_base am
            JOIN {q('dim_sku')} s USING (sku_id)
            {act_where}
            GROUP BY 1, 2, 3, 4, 5
        )
        SELECT
            fiscal_year, fiscal_month, division_id, brand_id, category_id,
            fc.version_id,
            fc.total_forecast_units,
            fc.total_forecast_dollars,
            act.sell_in_units,
            act.sell_in_dollars
        FROM fc
        FULL OUTER JOIN act
        USING (fiscal_year, fiscal_month, division_id, brand_id, category_id)
        ORDER BY fiscal_year, fiscal_month
        LIMIT 5000
    """
    return run_query(sql)


@router.get("/sku-detail")
def sku_detail(
    sku_id:      str,
    fiscal_year: Optional[int] = None,
    version_id:  Optional[str] = None,
):
    yr_fc  = f"AND fb.fiscal_year = {int(fiscal_year)}" if fiscal_year else ""
    yr_act = f"AND EXTRACT(YEAR FROM a.period_date) = {int(fiscal_year)}" if fiscal_year else ""
    sql = f"""
        WITH fc_base AS (
            SELECT f.* FROM {q('v_forecast_sellin')} f
            {_version_filter(version_id)}
        ),
        fc AS (
            SELECT
                fb.fiscal_year, fb.fiscal_month, fb.channel_type_id, fb.site_id,
                ANY_VALUE(fb.version)  AS version_id,
                SUM(fb.forecast_units) AS forecast_units
            FROM fc_base fb
            WHERE fb.sku_id = '{sku_id}' {yr_fc}
            GROUP BY 1, 2, 3, 4
        ),
        act AS (
            SELECT
                EXTRACT(YEAR  FROM a.period_date) AS fiscal_year,
                EXTRACT(MONTH FROM a.period_date) AS fiscal_month,
                a.channel_type_id, a.site_id,
                SUM(a.actual_units) AS actual_units
            FROM {q('fact_sellin_actuals')} a
            WHERE a.sku_id = '{sku_id}' {yr_act}
            GROUP BY 1, 2, 3, 4
        )
        SELECT
            fiscal_year, fiscal_month, channel_type_id, site_id,
            fc.version_id, fc.forecast_units, act.actual_units
        FROM fc
        FULL OUTER JOIN act USING (fiscal_year, fiscal_month, channel_type_id, site_id)
        ORDER BY fiscal_year, fiscal_month, channel_type_id
    """
    return run_query(sql)


@router.get("/top-skus")
def top_skus(
    fiscal_year:  Optional[int] = None,
    version_id:   Optional[str] = Query(default=None),
    division:     Optional[str] = None,
    channel_type: Optional[str] = None,
    limit:        int = 15,
):
    where = _dim_clauses(division, None, None, channel_type, fiscal_year, alias="fb")
    sql = f"""
        WITH fc_base AS (
            SELECT f.* FROM {q('v_forecast_sellin')} f
            {_version_filter(version_id)}
        )
        SELECT
            fb.sku_id,
            fb.channel_type_id,
            SUM(fb.forecast_units) AS forecast_units
        FROM fc_base fb
        JOIN {q('dim_sku')} s USING (sku_id)
        {where}
        GROUP BY 1, 2
        ORDER BY SUM(fb.forecast_units) DESC
        LIMIT {int(limit) * 10}
    """
    return run_query(sql)


@router.get("/version-compare")
def version_compare(
    version_a:   str,
    version_b:   str,
    fiscal_year: int,
    division:    Optional[str] = None,
):
    if version_a not in VALID_VERSIONS or version_b not in VALID_VERSIONS:
        return {"error": f"versions must be one of {sorted(VALID_VERSIONS)}"}
    div_filter = f"AND s.division_id = '{division}'" if division else ""
    sql = f"""
        WITH base AS (
            SELECT
                f.fiscal_month,
                f.version,
                SUM(f.forecast_units)                                  AS forecast_units,
                SUM(f.forecast_units * CAST(s.unit_price AS FLOAT64))  AS forecast_dollars
            FROM {q('v_forecast_sellin')} f
            JOIN {q('dim_sku')} s USING (sku_id)
            WHERE f.fiscal_year = {int(fiscal_year)}
              AND f.version IN ('{version_a}', '{version_b}')
              {div_filter}
            GROUP BY 1, 2
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
        WHERE a.version = '{version_a}'
          AND b.version = '{version_b}'
        ORDER BY fiscal_month
    """
    return run_query(sql)
