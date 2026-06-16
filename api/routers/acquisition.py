from fastapi import APIRouter
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])


@router.get("/overview")
def acquisition_overview():
    # New Hugimals SKUs summary
    new_skus = run_query(f"""
        SELECT
            s.sku_id, s.sku_name, s.division_id, s.brand_id,
            s.category_id, s.subcategory_id,
            s.unit_price, s.unit_cost, s.launch_date
        FROM {q('dim_sku')} s
        WHERE s.is_new_sku = TRUE
        ORDER BY s.sku_id
    """)

    # Comparable existing SKUs (same category, not new)
    comparable = run_query(f"""
        WITH new_cats AS (
            SELECT DISTINCT category_id FROM {q('dim_sku')} WHERE is_new_sku = TRUE
        ),
        existing AS (
            SELECT s.sku_id, s.sku_name, s.category_id, s.subcategory_id,
                   AVG(f.sell_in_units) AS avg_monthly_units
            FROM {q('dim_sku')} s
            JOIN {q('fact_financial_plan')} f ON s.sku_id = f.sku_id
            WHERE s.is_new_sku = FALSE
              AND s.category_id IN (SELECT category_id FROM new_cats)
              AND f.version_id = 'LATEST_EST'
            GROUP BY 1,2,3,4
        )
        SELECT * FROM existing ORDER BY avg_monthly_units DESC LIMIT 50
    """)

    # Supply risk: Hugimals SKUs with low forecast (possible channel gaps)
    risk_flags = run_query(f"""
        SELECT
            f.sku_id, s.sku_name, f.fiscal_year, f.fiscal_month,
            SUM(f.total_forecast_units) AS forecast_units,
            COUNT(DISTINCT f.key_account_id) AS account_count
        FROM {q('fact_financial_plan')} f
        JOIN {q('dim_sku')} s ON f.sku_id = s.sku_id
        WHERE s.is_new_sku = TRUE
          AND f.version_id = 'LATEST_EST'
          AND f.fiscal_year = 2024
        GROUP BY 1,2,3,4
        ORDER BY f.fiscal_month, f.sku_id
        LIMIT 500
    """)

    return {
        "new_sku_count":  len(new_skus),
        "new_skus":       new_skus,
        "comparable_skus": comparable,
        "supply_risk":    risk_flags,
    }
