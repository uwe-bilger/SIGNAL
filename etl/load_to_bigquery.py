"""
TASK_09 — Load all CSVs from GCS into BigQuery signal_dw.
Dims: loaded via pandas (preserves header column names for all-string tables).
Facts: loaded via GCS URI with autodetect (mixed types work correctly).

v6 data model: six single-purpose fact tables (nothing pre-merged) plus one
ops-domain table (fact_site_data_quality). version (Budget/LE01–LE11) and
lag_months are NEVER stored — the views below derive them from snapshot_date
vs target_period_date. Supply/inventory is out of scope (follow-up task).
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

# Legacy v5 objects removed by TASK_09 (wide pre-merged table, hardcoded
# LAG/LE version labels, retail POS framing).
LEGACY_TABLES = [
    "fact_financial_plan",
    "fact_pos_weekly",
    "fact_forecast_snapshot",
    "dim_version",
]
LEGACY_VIEWS = [
    "v_demand_plan_summary",
    "v_pos_monthly",
]


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

def load_fact(table_id: str, gcs_path: str):
    uri = f"gs://{BUCKET}/{gcs_path}"
    table_ref = f"{dataset_ref}.{table_id}"
    print(f"  Loading fact {gcs_path} -> {table_id}...", flush=True)
    try:
        client.delete_table(table_ref, not_found_ok=True)
        cfg = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
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
# Drop legacy v5 objects
# ---------------------------------------------------------------------------

def drop_legacy():
    for obj in LEGACY_VIEWS + LEGACY_TABLES:
        try:
            client.delete_table(f"{dataset_ref}.{obj}", not_found_ok=True)
            print(f"  dropped (if existed): {obj}")
        except Exception as e:
            print(f"  WARN could not drop {obj}: {e}")


# ---------------------------------------------------------------------------
# Views — the ONLY place version and lag_months exist. Both are derived:
#   version:    snapshot month Dec -> 'Budget' (budget set in December for
#               the next fiscal year); Jan..Nov -> LE01..LE11 (no LE12).
#   lag_months: whole months between snapshot month and target month.
# Forecast-vs-actuals comparison happens HERE (query time), never at rest.
# ---------------------------------------------------------------------------

VERSION_CASE = """
        CASE WHEN EXTRACT(MONTH FROM f.snapshot_date) = 12 THEN 'Budget'
             ELSE FORMAT('LE%02d', EXTRACT(MONTH FROM f.snapshot_date)) END
"""

def refresh_views():
    views = {
        # Sell-in forecast snapshots enriched with derived version + lag
        "v_forecast_sellin": f"""
            SELECT
                f.sku_id,
                f.site_id,
                f.channel_type_id,
                f.target_period_date,
                f.snapshot_date,
                EXTRACT(YEAR  FROM f.target_period_date) AS fiscal_year,
                EXTRACT(MONTH FROM f.target_period_date) AS fiscal_month,
                {VERSION_CASE} AS version,
                DATE_DIFF(f.target_period_date,
                          DATE_TRUNC(f.snapshot_date, MONTH), MONTH) AS lag_months,
                f.forecast_units
            FROM `{{ds}}.fact_forecast_sellin_snapshot` f
        """,
        # Sell-through forecast snapshots (Distributor/OEM only, by construction)
        "v_forecast_sellthrough": f"""
            SELECT
                f.sku_id,
                f.channel_type_id,
                f.target_period_date,
                f.snapshot_date,
                EXTRACT(YEAR  FROM f.target_period_date) AS fiscal_year,
                EXTRACT(MONTH FROM f.target_period_date) AS fiscal_month,
                {VERSION_CASE} AS version,
                DATE_DIFF(f.target_period_date,
                          DATE_TRUNC(f.snapshot_date, MONTH), MONTH) AS lag_months,
                f.forecast_units
            FROM `{{ds}}.fact_forecast_sellthrough_snapshot` f
        """,
        # Financial snapshots enriched with derived version + lag
        "v_financial_snapshot": f"""
            SELECT
                f.division_id,
                f.channel_type_id,
                f.category_id,
                f.target_period_date,
                f.snapshot_date,
                EXTRACT(YEAR  FROM f.target_period_date) AS fiscal_year,
                EXTRACT(MONTH FROM f.target_period_date) AS fiscal_month,
                {VERSION_CASE} AS version,
                DATE_DIFF(f.target_period_date,
                          DATE_TRUNC(f.snapshot_date, MONTH), MONTH) AS lag_months,
                f.revenue,
                f.cost,
                f.margin
            FROM `{{ds}}.fact_financial_snapshot` f
        """,
        # Forecast vs actuals — joined at QUERY TIME (the core TASK_09 rule:
        # this comparison is never stored as a row in a source table)
        "v_forecast_accuracy": """
            SELECT
                f.sku_id,
                f.site_id,
                f.channel_type_id,
                f.target_period_date,
                f.snapshot_date,
                f.version,
                f.lag_months,
                f.fiscal_year,
                f.fiscal_month,
                f.forecast_units,
                a.actual_units,
                a.actual_units - f.forecast_units                       AS error_units,
                SAFE_DIVIDE(a.actual_units - f.forecast_units,
                            a.actual_units)                             AS error_pct
            FROM `{ds}.v_forecast_sellin` f
            JOIN `{ds}.fact_sellin_actuals` a
              ON  a.sku_id          = f.sku_id
              AND a.site_id         = f.site_id
              AND a.channel_type_id = f.channel_type_id
              AND a.period_date     = f.target_period_date
            WHERE a.actual_units > 0
        """,
        # Monthly sell-through rollup (replaces retail-POS framing)
        "v_sellthrough_monthly": """
            SELECT
                a.sku_id,
                a.channel_type_id,
                EXTRACT(YEAR  FROM a.period_date) AS calendar_year,
                EXTRACT(MONTH FROM a.period_date) AS calendar_month,
                SUM(a.actual_units)                                        AS sellthrough_units,
                SUM(a.actual_units * CAST(s.unit_price AS FLOAT64))        AS sellthrough_dollars
            FROM `{ds}.fact_sellthrough_actuals` a
            JOIN `{ds}.dim_sku` s USING (sku_id)
            GROUP BY 1, 2, 3, 4
        """,
        # Exception flags per SKU/year from short-lag accuracy (bias + MAPE)
        "v_exception_flags": """
            SELECT
                s.sku_id,
                s.sku_name,
                s.division_id,
                s.is_new_sku,
                fa.fiscal_year,
                AVG(fa.error_pct)                                        AS mean_bias,
                AVG(ABS(fa.error_pct))                                   AS mape,
                CASE WHEN ABS(AVG(fa.error_pct)) > 0.15 THEN 1 ELSE 0 END AS bias_flag,
                CASE WHEN AVG(ABS(fa.error_pct)) > 0.35 THEN 1 ELSE 0 END AS accuracy_flag,
                MAX(CASE WHEN s.is_new_sku = 'True' THEN 1 ELSE 0 END)    AS new_sku_flag
            FROM `{ds}.v_forecast_accuracy` fa
            JOIN `{ds}.dim_sku` s USING (sku_id)
            WHERE fa.lag_months <= 3
            GROUP BY 1, 2, 3, 4, 5
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
            failures.append((view_id, str(e)))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate():
    sql = """
        SELECT 'dim_sku'                              AS tbl, COUNT(*) AS row_count FROM `{ds}.dim_sku`
        UNION ALL SELECT 'dim_time',                  COUNT(*) FROM `{ds}.dim_time`
        UNION ALL SELECT 'dim_channel_type',          COUNT(*) FROM `{ds}.dim_channel_type`
        UNION ALL SELECT 'dim_site',                  COUNT(*) FROM `{ds}.dim_site`
        UNION ALL SELECT 'fact_forecast_sellin_snapshot',      COUNT(*) FROM `{ds}.fact_forecast_sellin_snapshot`
        UNION ALL SELECT 'fact_forecast_sellthrough_snapshot', COUNT(*) FROM `{ds}.fact_forecast_sellthrough_snapshot`
        UNION ALL SELECT 'fact_sellin_actuals',                COUNT(*) FROM `{ds}.fact_sellin_actuals`
        UNION ALL SELECT 'fact_sellthrough_actuals',           COUNT(*) FROM `{ds}.fact_sellthrough_actuals`
        UNION ALL SELECT 'fact_financial_snapshot',            COUNT(*) FROM `{ds}.fact_financial_snapshot`
        UNION ALL SELECT 'fact_financial_actuals',             COUNT(*) FROM `{ds}.fact_financial_actuals`
        UNION ALL SELECT 'fact_site_data_quality',             COUNT(*) FROM `{ds}.fact_site_data_quality`
    """.replace("{ds}", dataset_ref)
    print("\nValidation counts:")
    for row in client.query(sql).result():
        print(f"  {row['tbl']:40s} {row['row_count']:>10,}")

    # Structural checks from the TASK_09 verification checklist
    checks = {
        "sellthrough fcst channels != Dist/OEM (want 0)": """
            SELECT COUNT(*) AS n FROM `{ds}.fact_forecast_sellthrough_snapshot`
            WHERE channel_type_id NOT IN ('CHN-02', 'CHN-03')
        """,
        "sellthrough actuals channels != Dist/OEM (want 0)": """
            SELECT COUNT(*) AS n FROM `{ds}.fact_sellthrough_actuals`
            WHERE channel_type_id NOT IN ('CHN-02', 'CHN-03')
        """,
        "snapshot dates not a 3rd Friday (want 0)": """
            SELECT COUNT(*) AS n FROM (
                SELECT DISTINCT snapshot_date FROM `{ds}.fact_forecast_sellin_snapshot`
                UNION DISTINCT
                SELECT DISTINCT snapshot_date FROM `{ds}.fact_forecast_sellthrough_snapshot`
                UNION DISTINCT
                SELECT DISTINCT snapshot_date FROM `{ds}.fact_financial_snapshot`
            )
            WHERE EXTRACT(DAYOFWEEK FROM snapshot_date) != 6  -- 6 = Friday
               OR EXTRACT(DAY FROM snapshot_date) NOT BETWEEN 15 AND 21
        """,
        "derived versions outside Budget/LE01-LE11 (want 0)": """
            SELECT COUNT(*) AS n FROM `{ds}.v_forecast_sellin`
            WHERE version NOT IN ('Budget','LE01','LE02','LE03','LE04','LE05',
                                  'LE06','LE07','LE08','LE09','LE10','LE11')
        """,
    }
    print("\nStructural checks:")
    for label, sql in checks.items():
        n = list(client.query(sql.replace("{ds}", dataset_ref)).result())[0]["n"]
        status = "ok" if n == 0 else "FAIL"
        print(f"  {status}  {label}: {n}")
        if n != 0:
            failures.append((label, f"{n} offending rows"))

    # Spot check: longer lag should be less accurate (higher MAPE)
    sql = """
        SELECT lag_months, AVG(ABS(error_pct)) AS mape
        FROM `{ds}.v_forecast_accuracy`
        GROUP BY lag_months ORDER BY lag_months
    """.replace("{ds}", dataset_ref)
    print("\nMAPE by lag (should broadly increase with lag):")
    for row in client.query(sql).result():
        print(f"  lag {row['lag_months']:>2}: MAPE {row['mape']:.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== TASK_09: Load to BigQuery (v6 six-table model) ===\n")

    print("[LEGACY CLEANUP]")
    drop_legacy()

    # Dimensions (all-string tables — use pandas to preserve column names)
    print("\n[DIMS]")
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
    load_dim("dim_promotion",        "dim_promotion.csv")
    load_dim("dim_site",             "dim_site.csv")
    # NOTE: dim_version intentionally not loaded — version is derived, never stored.

    # Facts — six single-purpose tables + one ops table
    print("\n[FACTS]")
    load_fact("fact_forecast_sellin_snapshot",      "raw/facts/fact_forecast_sellin_snapshot.csv")
    load_fact("fact_forecast_sellthrough_snapshot", "raw/facts/fact_forecast_sellthrough_snapshot.csv")
    load_fact("fact_sellin_actuals",                "raw/facts/fact_sellin_actuals.csv")
    load_fact("fact_sellthrough_actuals",           "raw/facts/fact_sellthrough_actuals.csv")
    load_fact("fact_financial_snapshot",            "raw/facts/fact_financial_snapshot.csv")
    load_fact("fact_financial_actuals",             "raw/facts/fact_financial_actuals.csv")
    load_fact("fact_site_data_quality",             "raw/facts/fact_site_data_quality.csv")

    print("\n[VIEWS]")
    refresh_views()

    validate()

    print(f"\nDone. Successes: {len(successes)}  Failures: {len(failures)}")
    for t, e in failures:
        print(f"  FAILED: {t} -- {e}")


if __name__ == "__main__":
    main()
