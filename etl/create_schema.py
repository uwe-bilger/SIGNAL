"""TASK_01 — Create BigQuery dataset, dimension tables, fact tables, and views."""

import os
from google.cloud import bigquery

PROJECT = "signal-499604"
DATASET = "signal_dw"
LOCATION = "US"

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "..", "secrets", "signal-key.json"),
)

client = bigquery.Client(project=PROJECT)


def create_dataset():
    ds = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    ds.location = LOCATION
    client.create_dataset(ds, exists_ok=True)
    print(f"Dataset {DATASET} ready.")


DIMENSIONS = {
    "dim_division": [
        bigquery.SchemaField("division_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("division_name", "STRING"),
    ],
    "dim_brand": [
        bigquery.SchemaField("brand_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("brand_name", "STRING"),
        bigquery.SchemaField("division_id", "STRING"),
    ],
    "dim_product_line": [
        bigquery.SchemaField("product_line_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_line_name", "STRING"),
        bigquery.SchemaField("brand_id", "STRING"),
    ],
    "dim_sub_product_line": [
        bigquery.SchemaField("sub_product_line_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sub_product_line_name", "STRING"),
        bigquery.SchemaField("product_line_id", "STRING"),
    ],
    "dim_major_category": [
        bigquery.SchemaField("major_category_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("major_category_name", "STRING"),
    ],
    "dim_category": [
        bigquery.SchemaField("category_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category_name", "STRING"),
        bigquery.SchemaField("major_category_id", "STRING"),
    ],
    "dim_subcategory": [
        bigquery.SchemaField("subcategory_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("subcategory_name", "STRING"),
        bigquery.SchemaField("category_id", "STRING"),
    ],
    "dim_sku": [
        bigquery.SchemaField("sku_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sku_name", "STRING"),
        bigquery.SchemaField("division_id", "STRING"),
        bigquery.SchemaField("brand_id", "STRING"),
        bigquery.SchemaField("product_line_id", "STRING"),
        bigquery.SchemaField("sub_product_line_id", "STRING"),
        bigquery.SchemaField("major_category_id", "STRING"),
        bigquery.SchemaField("category_id", "STRING"),
        bigquery.SchemaField("subcategory_id", "STRING"),
        bigquery.SchemaField("unit_cost", "FLOAT64"),
        bigquery.SchemaField("unit_price", "FLOAT64"),
        bigquery.SchemaField("launch_date", "DATE"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("is_new_sku", "BOOL"),
    ],
    "dim_channel_type": [
        bigquery.SchemaField("channel_type_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_type_name", "STRING"),
    ],
    "dim_market": [
        bigquery.SchemaField("market_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market_name", "STRING"),
        bigquery.SchemaField("channel_type_id", "STRING"),
    ],
    "dim_customer_group": [
        bigquery.SchemaField("customer_group_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("customer_group_name", "STRING"),
        bigquery.SchemaField("market_id", "STRING"),
    ],
    "dim_key_account": [
        bigquery.SchemaField("key_account_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("key_account_name", "STRING"),
        bigquery.SchemaField("customer_group_id", "STRING"),
        bigquery.SchemaField("channel_type_id", "STRING"),
    ],
    "dim_time": [
        bigquery.SchemaField("date_id", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("fiscal_year", "INT64"),
        bigquery.SchemaField("fiscal_quarter", "INT64"),
        bigquery.SchemaField("fiscal_month", "INT64"),
        bigquery.SchemaField("fiscal_week", "INT64"),
        bigquery.SchemaField("fiscal_period_name", "STRING"),
        bigquery.SchemaField("is_partial_week", "BOOL"),
        bigquery.SchemaField("partial_week_month_split", "STRING"),
        bigquery.SchemaField("calendar_year", "INT64"),
        bigquery.SchemaField("calendar_month", "INT64"),
        bigquery.SchemaField("calendar_week", "INT64"),
        bigquery.SchemaField("day_of_week", "INT64"),
        bigquery.SchemaField("is_weekend", "BOOL"),
        bigquery.SchemaField("gregorian_month_name", "STRING"),
        bigquery.SchemaField("fiscal_445_pattern", "STRING"),
    ],
    "dim_version": [
        bigquery.SchemaField("version_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("version_name", "STRING"),
        bigquery.SchemaField("version_type", "STRING"),
        bigquery.SchemaField("version_order", "INT64"),
        bigquery.SchemaField("lag_months", "INT64"),
    ],
    "dim_promotion": [
        bigquery.SchemaField("promotion_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("promotion_name", "STRING"),
        bigquery.SchemaField("promotion_type", "STRING"),
        bigquery.SchemaField("start_date", "DATE"),
        bigquery.SchemaField("end_date", "DATE"),
        bigquery.SchemaField("sku_id", "STRING"),
        bigquery.SchemaField("key_account_id", "STRING"),
        bigquery.SchemaField("expected_lift_pct", "FLOAT64"),
    ],
}

FACTS = {
    "fact_financial_plan": [
        bigquery.SchemaField("record_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sku_id", "STRING"),
        bigquery.SchemaField("key_account_id", "STRING"),
        bigquery.SchemaField("fiscal_year", "INT64"),
        bigquery.SchemaField("fiscal_month", "INT64"),
        bigquery.SchemaField("version_id", "STRING"),
        bigquery.SchemaField("sell_in_units", "FLOAT64"),
        bigquery.SchemaField("sell_in_dollars", "FLOAT64"),
        bigquery.SchemaField("sell_through_units", "FLOAT64"),
        bigquery.SchemaField("sell_through_dollars", "FLOAT64"),
        bigquery.SchemaField("corrected_history_units", "FLOAT64"),
        bigquery.SchemaField("stat_forecast_units", "FLOAT64"),
        bigquery.SchemaField("manual_override_units", "FLOAT64"),
        bigquery.SchemaField("promo_uplift_units", "FLOAT64"),
        bigquery.SchemaField("total_forecast_units", "FLOAT64"),
        bigquery.SchemaField("total_forecast_dollars", "FLOAT64"),
        bigquery.SchemaField("inventory_on_hand_units", "FLOAT64"),
        bigquery.SchemaField("weeks_of_supply", "FLOAT64"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP"),
    ],
    "fact_pos_weekly": [
        bigquery.SchemaField("record_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sku_id", "STRING"),
        bigquery.SchemaField("key_account_id", "STRING"),
        bigquery.SchemaField("date_id", "DATE"),
        bigquery.SchemaField("fiscal_year", "INT64"),
        bigquery.SchemaField("fiscal_week", "INT64"),
        bigquery.SchemaField("is_partial_week", "BOOL"),
        bigquery.SchemaField("pos_units", "FLOAT64"),
        bigquery.SchemaField("pos_dollars", "FLOAT64"),
        bigquery.SchemaField("inventory_on_hand_units", "FLOAT64"),
        bigquery.SchemaField("weeks_of_supply", "FLOAT64"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP"),
    ],
    "fact_forecast_snapshot": [
        bigquery.SchemaField("record_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sku_id", "STRING"),
        bigquery.SchemaField("key_account_id", "STRING"),
        bigquery.SchemaField("fiscal_year", "INT64"),
        bigquery.SchemaField("fiscal_month", "INT64"),
        bigquery.SchemaField("version_id", "STRING"),
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("forecast_units", "FLOAT64"),
        bigquery.SchemaField("actual_units", "FLOAT64"),
        bigquery.SchemaField("forecast_error_units", "FLOAT64"),
        bigquery.SchemaField("forecast_error_pct", "FLOAT64"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP"),
    ],
}

VIEWS = {
    "v_demand_plan_summary": f"""
        SELECT
            d.division_name,
            b.brand_name,
            cat.category_name,
            ct.channel_type_name,
            fp.fiscal_year,
            fp.fiscal_month,
            fp.version_id,
            SUM(fp.sell_in_units)          AS sell_in_units,
            SUM(fp.sell_in_dollars)        AS sell_in_dollars,
            SUM(fp.sell_through_units)     AS sell_through_units,
            SUM(fp.sell_through_dollars)   AS sell_through_dollars,
            SUM(fp.total_forecast_units)   AS total_forecast_units,
            SUM(fp.total_forecast_dollars) AS total_forecast_dollars,
            SUM(fp.inventory_on_hand_units) AS inventory_on_hand_units
        FROM `{PROJECT}.{DATASET}.fact_financial_plan` fp
        JOIN `{PROJECT}.{DATASET}.dim_sku`          s   ON fp.sku_id          = s.sku_id
        JOIN `{PROJECT}.{DATASET}.dim_division`     d   ON s.division_id      = d.division_id
        JOIN `{PROJECT}.{DATASET}.dim_brand`        b   ON s.brand_id         = b.brand_id
        JOIN `{PROJECT}.{DATASET}.dim_category`     cat ON s.category_id      = cat.category_id
        JOIN `{PROJECT}.{DATASET}.dim_key_account`  ka  ON fp.key_account_id  = ka.key_account_id
        JOIN `{PROJECT}.{DATASET}.dim_channel_type` ct  ON ka.channel_type_id = ct.channel_type_id
        GROUP BY 1,2,3,4,5,6,7
    """,
    "v_forecast_accuracy": f"""
        SELECT
            fs.sku_id,
            s.sku_name,
            d.division_name,
            fs.key_account_id,
            ka.key_account_name,
            fs.fiscal_year,
            fs.fiscal_month,
            fs.version_id,
            v.lag_months,
            fs.forecast_units,
            fs.actual_units,
            fs.forecast_error_units,
            fs.forecast_error_pct,
            AVG(ABS(fs.forecast_error_pct))
                OVER (PARTITION BY fs.sku_id, fs.version_id) AS mape
        FROM `{PROJECT}.{DATASET}.fact_forecast_snapshot` fs
        JOIN `{PROJECT}.{DATASET}.dim_sku`         s  ON fs.sku_id         = s.sku_id
        JOIN `{PROJECT}.{DATASET}.dim_division`    d  ON s.division_id     = d.division_id
        JOIN `{PROJECT}.{DATASET}.dim_key_account` ka ON fs.key_account_id = ka.key_account_id
        JOIN `{PROJECT}.{DATASET}.dim_version`     v  ON fs.version_id     = v.version_id
    """,
    "v_pos_monthly": f"""
        SELECT
            pw.sku_id,
            pw.key_account_id,
            t.fiscal_year,
            t.fiscal_month,
            t.gregorian_month_name,
            SUM(pw.pos_units)              AS pos_units,
            SUM(pw.pos_dollars)            AS pos_dollars,
            AVG(pw.inventory_on_hand_units) AS avg_inventory_on_hand_units,
            AVG(pw.weeks_of_supply)        AS avg_weeks_of_supply
        FROM `{PROJECT}.{DATASET}.fact_pos_weekly` pw
        JOIN `{PROJECT}.{DATASET}.dim_time` t ON pw.date_id = t.date_id
        GROUP BY 1,2,3,4,5
    """,
    "v_exception_flags": f"""
        SELECT
            fp.sku_id,
            s.sku_name,
            s.is_new_sku,
            fp.key_account_id,
            fp.fiscal_year,
            fp.fiscal_month,
            fp.version_id,
            fp.total_forecast_units,
            fp.stat_forecast_units,
            fp.weeks_of_supply,
            CASE
                WHEN fp.stat_forecast_units > 0
                     AND (fp.total_forecast_units / fp.stat_forecast_units > 1.2
                          OR fp.total_forecast_units / fp.stat_forecast_units < 0.8)
                THEN TRUE ELSE FALSE
            END AS manual_override_flag,
            CASE WHEN fp.weeks_of_supply < 4 THEN TRUE ELSE FALSE END AS stock_risk_flag,
            s.is_new_sku AS ma_flag,
            acc.high_error_flag
        FROM `{PROJECT}.{DATASET}.fact_financial_plan` fp
        JOIN `{PROJECT}.{DATASET}.dim_sku` s ON fp.sku_id = s.sku_id
        LEFT JOIN (
            SELECT
                sku_id,
                TRUE AS high_error_flag
            FROM (
                SELECT
                    sku_id,
                    AVG(ABS(forecast_error_pct)) AS avg_error
                FROM `{PROJECT}.{DATASET}.fact_forecast_snapshot`
                WHERE version_id IN ('LAG1','LAG2','LAG3')
                GROUP BY sku_id
            )
            WHERE avg_error > 0.20
        ) acc ON fp.sku_id = acc.sku_id
    """,
}


def create_tables(table_map):
    for name, schema in table_map.items():
        ref = f"{PROJECT}.{DATASET}.{name}"
        table = bigquery.Table(ref, schema=schema)
        client.create_table(table, exists_ok=True)
        print(f"  Table {name} ready.")


def create_views():
    for name, query in VIEWS.items():
        ref = f"{PROJECT}.{DATASET}.{name}"
        view = bigquery.Table(ref)
        view.view_query = query.strip()
        try:
            client.create_table(view)
        except Exception:
            # View exists — update the query
            existing = client.get_table(ref)
            existing.view_query = query.strip()
            client.update_table(existing, ["view_query"])
        print(f"  View {name} ready.")


def verify():
    result = client.query(
        f"SELECT COUNT(*) AS cnt FROM `{PROJECT}.{DATASET}.dim_version`"
    ).result()
    for row in result:
        print(f"\nVerification: dim_version row count = {row.cnt} (expected 0)")


if __name__ == "__main__":
    print("=== TASK_01: Creating BigQuery schema ===\n")
    create_dataset()
    print("\nCreating dimension tables...")
    create_tables(DIMENSIONS)
    print("\nCreating fact tables...")
    create_tables(FACTS)
    print("\nCreating views...")
    create_views()
    verify()
    print("\nDone.")
