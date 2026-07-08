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

    TASK_09: data quality now lives in its own ops table
    (fact_site_data_quality) — the demand/financial fact tables carry exactly
    their spec'd fields and nothing else.
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

    # Data quality trend by site — monthly score over the last ~2.5 years
    dq_trend = run_query(f"""
        SELECT
            dq.site_id,
            EXTRACT(YEAR  FROM dq.period_date) AS fiscal_year,
            EXTRACT(MONTH FROM dq.period_date) AS fiscal_month,
            AVG(dq.data_quality_score) AS avg_data_quality,
            COUNT(*)                   AS record_count
        FROM {q('fact_site_data_quality')} dq
        WHERE EXTRACT(YEAR FROM dq.period_date) >= 2024
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """)

    # Pre- vs post-acquisition summary — actuals joined to dim_time and
    # dim_sku (for dollars) at QUERY TIME; nothing pre-merged at rest.
    acquisition_summary = run_query(f"""
        SELECT
            t.is_pre_acquisition,
            s.division_id,
            COUNT(DISTINCT a.sku_id)                              AS sku_count,
            SUM(a.actual_units)                                   AS total_units,
            SUM(a.actual_units * CAST(s.unit_price AS FLOAT64))   AS total_dollars,
            AVG(dq.data_quality_score)                            AS avg_data_quality
        FROM {q('fact_sellin_actuals')} a
        JOIN {q('dim_time')} t ON CAST(t.date_id AS DATE) = a.period_date
        JOIN {q('dim_sku')}  s ON a.sku_id = s.sku_id
        LEFT JOIN {q('fact_site_data_quality')} dq
          ON dq.site_id = a.site_id AND dq.period_date = a.period_date
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

    # WFA trend — 1 - MAPE at lag 1, lag DERIVED in the accuracy view
    wfa_trend = run_query(f"""
        SELECT
            fa.fiscal_year,
            fa.fiscal_month,
            s.division_id,
            COUNT(*)                   AS snapshots,
            AVG(ABS(fa.error_pct))     AS mape,
            1 - AVG(ABS(fa.error_pct)) AS wfa_estimate
        FROM {q('v_forecast_accuracy')} fa
        JOIN {q('dim_sku')} s USING (sku_id)
        WHERE fa.lag_months = 1
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """)

    # Channel coverage risk for new SKUs (few channels = qualification gap)
    new_sku_risk = run_query(f"""
        SELECT
            f.sku_id,
            s.sku_name,
            f.fiscal_year,
            f.fiscal_month,
            SUM(f.forecast_units)               AS forecast_units,
            COUNT(DISTINCT f.channel_type_id)   AS channel_count,
            AVG(dq.data_quality_score)          AS avg_dq_score
        FROM {q('v_forecast_sellin')} f
        JOIN {q('dim_sku')} s USING (sku_id)
        LEFT JOIN {q('fact_site_data_quality')} dq
          ON dq.site_id = f.site_id AND dq.period_date = f.target_period_date
        WHERE s.is_new_sku = 'True'
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
