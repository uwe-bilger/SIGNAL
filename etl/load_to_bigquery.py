"""
TASK_03 — Load all CSVs from GCS into BigQuery signal_dw.
Dims: loaded via pandas (preserves header column names for all-string tables).
Facts: loaded via GCS URI with autodetect (mixed types work correctly).
"""

import os
from pathlib import Path
import pandas as pd
from google.cloud import bigquery

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      str(Path(__file__).parent.parent / "secrets" / "signal-key.json"))

PROJECT    = "signal-499604"
DATASET    = "signal_dw"
BUCKET     = "signal-raw-data"
LOCAL_DIMS = Path(__file__).parent / "mock_data" / "dimensions"
LOCAL_FACTS= Path(__file__).parent / "mock_data" / "facts"

client      = bigquery.Client(project=PROJECT)
dataset_ref = f"{PROJECT}.{DATASET}"

failures  = []
successes = []


# ---------------------------------------------------------------------------
# Load a dimension table from local CSV via pandas DataFrame
# ---------------------------------------------------------------------------

def load_dim(table_id: str, csv_name: str):
    path = LOCAL_DIMS / csv_name
    table_ref = f"{dataset_ref}.{table_id}"
    print(f"  Loading dim {table_id} from {csv_name}...", flush=True)
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        client.delete_table(table_ref, not_found_ok=True)
        job = client.load_table_from_dataframe(df, table_ref)
        job.result()
        t = client.get_table(table_ref)
        print(f"  ok {table_id}: {t.num_rows} rows | cols: {[f.name for f in t.schema]}")
        successes.append(table_id)
    except Exception as e:
        print(f"  FAIL {table_id}: {e}")
        failures.append((table_id, str(e)))


# ---------------------------------------------------------------------------
# Load a fact table from GCS URI (autodetect works for mixed-type CSVs)
# ---------------------------------------------------------------------------

def load_fact(table_id: str, gcs_path: str, write_disposition: str):
    uri = f"gs://{BUCKET}/{gcs_path}"
    table_ref = f"{dataset_ref}.{table_id}"
    disp = getattr(bigquery.WriteDisposition, write_disposition)
    print(f"  Loading fact {gcs_path} -> {table_id} ({write_disposition})...", flush=True)
    try:
        if write_disposition == "WRITE_TRUNCATE":
            client.delete_table(table_ref, not_found_ok=True)
        cfg = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=disp,
        )
        job = client.load_table_from_uri(uri, table_ref, job_config=cfg)
        job.result()
        t = client.get_table(table_ref)
        print(f"  ok {table_id}: {t.num_rows} rows total")
        successes.append(table_id)
    except Exception as e:
        print(f"  FAIL {table_id}: {e}")
        failures.append((table_id, str(e)))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def refresh_views():
    views = {
        "v_demand_plan_summary": """
            SELECT
                s.division_id,
                s.brand_id,
                s.category_id,
                ka.channel_type_id,
                f.fiscal_year,
                f.fiscal_month,
                f.version_id,
                SUM(f.sell_in_units)          AS total_sell_in_units,
                SUM(f.sell_in_dollars)        AS total_sell_in_dollars,
                SUM(f.total_forecast_units)   AS total_forecast_units,
                SUM(f.total_forecast_dollars) AS total_forecast_dollars
            FROM `{ds}.fact_financial_plan` f
            JOIN `{ds}.dim_sku`         s  ON f.sku_id         = s.sku_id
            JOIN `{ds}.dim_key_account` ka ON f.key_account_id = ka.key_account_id
            GROUP BY 1,2,3,4,5,6,7
        """,
        "v_forecast_accuracy": """
            SELECT
                fs.fiscal_year,
                fs.fiscal_month,
                fs.version_id,
                v.lag_months,
                s.division_id,
                s.category_id,
                COUNT(*)                                        AS snapshots,
                AVG(ABS(SAFE_CAST(fs.forecast_error_pct AS FLOAT64))) AS mape,
                AVG(SAFE_CAST(fs.forecast_error_pct AS FLOAT64))      AS mean_bias,
                AVG(fs.actual_units)                            AS avg_actual_units
            FROM `{ds}.fact_forecast_snapshot` fs
            JOIN `{ds}.dim_version` v ON fs.version_id = v.version_id
            JOIN `{ds}.dim_sku`     s ON fs.sku_id     = s.sku_id
            WHERE fs.actual_units IS NOT NULL
              AND fs.actual_units > 0
            GROUP BY 1,2,3,4,5,6
        """,
        "v_pos_monthly": """
            SELECT
                p.sku_id,
                p.key_account_id,
                t.calendar_year,
                t.calendar_month,
                t.calendar_month_name,
                SUM(p.pos_units * CAST(t.partial_week_proration_factor AS FLOAT64))   AS pos_units_monthly,
                SUM(p.pos_dollars * CAST(t.partial_week_proration_factor AS FLOAT64)) AS pos_dollars_monthly,
                AVG(p.inventory_on_hand_units)                       AS avg_inventory,
                AVG(p.weeks_of_supply)                               AS avg_wos
            FROM `{ds}.fact_pos_weekly` p
            JOIN `{ds}.dim_time` t ON p.date_id = CAST(t.date_id AS DATE)
            GROUP BY 1,2,3,4,5
        """,
        "v_exception_flags": """
            SELECT
                s.sku_id,
                s.sku_name,
                s.division_id,
                s.is_new_sku,
                MAX(CASE WHEN ABS(f.total_forecast_units - f.stat_forecast_units)
                              / NULLIF(f.stat_forecast_units, 0) > 0.10 THEN 1 ELSE 0 END) AS override_flag,
                MAX(CASE WHEN f.weeks_of_supply < 4 THEN 1 ELSE 0 END) AS stock_risk_flag,
                MAX(CAST(s.is_new_sku AS INT64)) AS new_sku_flag
            FROM `{ds}.fact_financial_plan` f
            JOIN `{ds}.dim_sku` s ON f.sku_id = s.sku_id
            GROUP BY s.sku_id, s.sku_name, s.division_id, s.is_new_sku
        """,
    }

    for view_id, query in views.items():
        sql = query.replace("{ds}", dataset_ref)
        table_ref = f"{dataset_ref}.{view_id}"
        vt = bigquery.Table(table_ref)
        vt.view_query = sql
        try:
            client.delete_table(table_ref, not_found_ok=True)
            client.create_table(vt)
            print(f"  ok view {view_id}")
        except Exception as e:
            print(f"  FAIL view {view_id}: {e}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate():
    sql = """
        SELECT 'dim_sku'                AS tbl, COUNT(*) AS row_count FROM `{ds}.dim_sku`
        UNION ALL SELECT 'dim_time',     COUNT(*) FROM `{ds}.dim_time`
        UNION ALL SELECT 'dim_version',  COUNT(*) FROM `{ds}.dim_version`
        UNION ALL SELECT 'dim_channel_type', COUNT(*) FROM `{ds}.dim_channel_type`
        UNION ALL SELECT 'fact_financial_plan', COUNT(*) FROM `{ds}.fact_financial_plan`
        UNION ALL SELECT 'fact_pos_weekly', COUNT(*) FROM `{ds}.fact_pos_weekly`
        UNION ALL SELECT 'fact_forecast_snapshot', COUNT(*) FROM `{ds}.fact_forecast_snapshot`
    """.replace("{ds}", dataset_ref)
    print("\nValidation counts:")
    for row in client.query(sql).result():
        print(f"  {row['tbl']:35s} {row['row_count']:>10,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== TASK_03: Load to BigQuery ===\n")

    # Dimensions (all-string tables — use pandas to preserve column names)
    print("[DIMS]")
    load_dim("dim_division",         "dim_division.csv")
    load_dim("dim_brand",            "dim_brand.csv")
    load_dim("dim_major_category",   "dim_major_category.csv")
    load_dim("dim_category",         "dim_category.csv")
    load_dim("dim_subcategory",      "dim_subcategory.csv")
    load_dim("dim_product_line",     "dim_product_line.csv")
    load_dim("dim_sub_product_line", "dim_sub_product_line.csv")
    load_dim("dim_sku",              "dim_sku.csv")
    load_dim("dim_channel_type",     "dim_channel_type.csv")
    load_dim("dim_market",           "dim_market.csv")
    load_dim("dim_customer_group",   "dim_customer_group.csv")
    load_dim("dim_key_account",      "dim_key_account.csv")
    load_dim("dim_time",             "dim_time.csv")
    load_dim("dim_version",          "dim_version.csv")
    load_dim("dim_promotion",        "dim_promotion.csv")

    # Facts (mixed types — GCS URI + autodetect works correctly)
    print("\n[FACTS]")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2020.csv", "WRITE_TRUNCATE")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2021.csv", "WRITE_APPEND")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2022.csv", "WRITE_APPEND")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2023.csv", "WRITE_APPEND")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2024.csv", "WRITE_APPEND")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2025.csv", "WRITE_APPEND")
    load_fact("fact_financial_plan", "raw/facts/fact_financial_plan_2026.csv", "WRITE_APPEND")
    load_fact("fact_pos_weekly",        "raw/facts/fact_pos_weekly.csv",         "WRITE_TRUNCATE")
    load_fact("fact_forecast_snapshot", "raw/facts/fact_forecast_snapshot.csv",  "WRITE_TRUNCATE")

    print("\n[VIEWS]")
    refresh_views()

    validate()

    print(f"\nDone. Successes: {len(successes)}  Failures: {len(failures)}")
    for t, e in failures:
        print(f"  FAILED: {t} -- {e}")


if __name__ == "__main__":
    main()
