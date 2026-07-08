from fastapi import APIRouter
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])

# TASK_09: version is DERIVED (snapshot month -> Budget / LE01..LE11), never a
# stored column. The domain is a property of the planning calendar, so it is
# enumerated here rather than read from a dim table (dim_version is gone).
VERSIONS = (
    [{"version_id": "Budget", "version_name": "Annual Budget (Dec snapshot)",
      "version_type": "Derived", "version_order": 0, "is_financial": True}]
    + [{"version_id": f"LE{i:02d}", "version_name": f"Latest Estimate {i:02d}",
        "version_type": "Derived", "version_order": i, "is_financial": True}
       for i in range(1, 12)]   # LE01..LE11 — there is no LE12
)


@router.get("")
def get_dimensions():
    divisions     = run_query(f"SELECT division_id, division_name FROM {q('dim_division')} ORDER BY division_name")
    brands        = run_query(f"SELECT brand_id, brand_name, division_id FROM {q('dim_brand')} ORDER BY brand_name")
    categories    = run_query(f"SELECT category_id, category_name, major_category_id FROM {q('dim_category')} ORDER BY category_name")
    channel_types = run_query(f"SELECT channel_type_id, channel_type_name FROM {q('dim_channel_type')} ORDER BY channel_type_name")
    markets       = run_query(f"SELECT market_id, market_name, channel_type_id FROM {q('dim_market')} ORDER BY market_name")
    key_accounts  = run_query(f"SELECT key_account_id, key_account_name, channel_type_id FROM {q('dim_key_account')} ORDER BY key_account_name")
    sites         = run_query(f"SELECT site_id, site_name, migration_status, is_placeholder_site FROM {q('dim_site')} ORDER BY site_id")
    fiscal_years  = run_query(f"SELECT DISTINCT fiscal_year FROM {q('v_forecast_sellin')} ORDER BY fiscal_year")

    return {
        "divisions":     divisions,
        "brands":        brands,
        "categories":    categories,
        "channel_types": channel_types,
        "markets":       markets,
        "key_accounts":  key_accounts,
        "sites":         sites,
        "versions":      VERSIONS,
        "fiscal_years":  [r["fiscal_year"] for r in fiscal_years],
    }
