from fastapi import APIRouter
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])


@router.get("")
def get_dimensions():
    divisions     = run_query(f"SELECT division_id, division_name FROM {q('dim_division')} ORDER BY division_name")
    brands        = run_query(f"SELECT brand_id, brand_name, division_id FROM {q('dim_brand')} ORDER BY brand_name")
    categories    = run_query(f"SELECT category_id, category_name, major_category_id FROM {q('dim_category')} ORDER BY category_name")
    channel_types = run_query(f"SELECT channel_type_id, channel_type_name FROM {q('dim_channel_type')} ORDER BY channel_type_name")
    markets       = run_query(f"SELECT market_id, market_name, channel_type_id FROM {q('dim_market')} ORDER BY market_name")
    key_accounts  = run_query(f"SELECT key_account_id, key_account_name, channel_type_id FROM {q('dim_key_account')} ORDER BY key_account_name")
    versions      = run_query(f"SELECT version_id, version_name, version_type, version_order FROM {q('dim_version')} ORDER BY version_order")
    fiscal_years  = run_query(f"SELECT DISTINCT fiscal_year FROM {q('fact_financial_plan')} ORDER BY fiscal_year")

    return {
        "divisions":     divisions,
        "brands":        brands,
        "categories":    categories,
        "channel_types": channel_types,
        "markets":       markets,
        "key_accounts":  key_accounts,
        "versions":      versions,
        "fiscal_years":  [r["fiscal_year"] for r in fiscal_years],
    }
