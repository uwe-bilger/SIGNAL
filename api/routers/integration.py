from fastapi import APIRouter
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/integration", tags=["integration"])


@router.get("/overview")
def integration_overview():
    """
    FSD Integration dashboard data.

    Two-layer story:
    1. Whole-of-FSD acquisition boundary (Sept 2025): all prior data is
       legacy Solventum/3M history, with lower data quality and no formal SIOP.
    2. Per-site ERP migration wave: each site transitions from legacy SAP to
       Oracle JDE on its planned cutover date, creating a visible, dateable
       data-quality step change.
    """

    # ERP migration status by site
    sites = run_query(f"""
        SELECT
            site_id, site_name, city, state_or_region, country,
            business_lines_served,
            legacy_erp, target_erp,
            migration_wave, planned_cutover_date, migration_status,
            is_placeholder_site
        FROM {q('dim_site')}
        ORDER BY migration_wave, site_id
    """)

    # Data quality trend by site — monthly average score over the last 24 months
    dq_trend = run_query(f"""
        SELECT
            f.site_id,
            f.fiscal_year,
            f.fiscal_month,
            AVG(CAST(f.data_quality_score AS FLOAT64)) AS avg_data_quality,
            COUNT(*) AS record_count
        FROM {q('fact_financial_plan')} f
        WHERE f.version_id = 'LATEST_EST'
          AND f.fiscal_year >= 2024
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """)

    # Pre-acquisition vs post-acquisition summary
    acquisition_summary = run_query(f"""
        SELECT
            t.is_pre_acquisition,
            s.division_id,
            COUNT(DISTINCT f.sku_id)         AS sku_count,
            SUM(f.sell_in_units)             AS total_units,
            SUM(f.sell_in_dollars)           AS total_dollars,
            AVG(CAST(f.data_quality_score AS FLOAT64)) AS avg_data_quality
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_time')} t
          ON CAST(t.date_id AS DATE) = DATE(f.fiscal_year, f.fiscal_month, 1)
        JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
        WHERE f.version_id = 'LATEST_EST'
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)

    # Post-acquisition new SKUs (introduced after TF R&D resources applied)
    new_skus = run_query(f"""
        SELECT
            s.sku_id, s.sku_name, s.division_id, s.brand_id,
            s.category_id, s.unit_price, s.unit_cost, s.launch_date
        FROM {q('dim_sku')} s
        WHERE s.is_new_sku = 'True'
        ORDER BY s.launch_date, s.sku_id
    """)

    # WFA trend (derived from forecast snapshot — 1 - MAPE at LAG1)
    wfa_trend = run_query(f"""
        SELECT
            fs.fiscal_year,
            fs.fiscal_month,
            s.division_id,
            COUNT(*) AS snapshots,
            AVG(ABS(SAFE_CAST(fs.forecast_error_pct AS FLOAT64))) AS mape,
            1 - AVG(ABS(SAFE_CAST(fs.forecast_error_pct AS FLOAT64))) AS wfa_estimate
        FROM {q('fact_forecast_snapshot')} fs
        JOIN {q('dim_sku')} s ON fs.sku_id = s.sku_id
        WHERE fs.version_id = 'LAG1'
          AND SAFE_CAST(fs.forecast_error_pct AS FLOAT64) IS NOT NULL
          AND fs.actual_units > 0
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """)

    # Supply risk for new SKUs (low forecast coverage = channel gap)
    new_sku_risk = run_query(f"""
        SELECT
            f.sku_id,
            s.sku_name,
            f.fiscal_year,
            f.fiscal_month,
            SUM(f.total_forecast_units)    AS forecast_units,
            COUNT(DISTINCT f.key_account_id) AS account_count,
            AVG(CAST(f.data_quality_score AS FLOAT64)) AS avg_dq_score
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
        WHERE s.is_new_sku = 'True'
          AND f.version_id = 'LATEST_EST'
          AND f.fiscal_year = 2026
        GROUP BY 1, 2, 3, 4
        ORDER BY f.fiscal_month, f.sku_id
        LIMIT 200
    """)

    return {
        "sites":                sites,
        "dq_trend":             dq_trend,
        "acquisition_summary":  acquisition_summary,
        "new_skus":             new_skus,
        "wfa_trend":            wfa_trend,
        "new_sku_risk":         new_sku_risk,
    }
