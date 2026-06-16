# TASK_03 — ETL: Load CSV Data into BigQuery

## Objective
Load all CSV files from GCS into BigQuery tables in `signal_dw`.
Validate row counts and data integrity after loading.

## Prerequisites
- TASK_01 complete (schema exists)
- TASK_02 complete (CSVs in GCS)
- `./secrets/signal-key.json` exists

## Environment setup
```bash
pip install google-cloud-bigquery google-cloud-storage pandas
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/signal-key.json
```

## Create ETL script
Create `./etl/load_to_bigquery.py` with the following behavior:

### Loading order (respect FK dependencies)
1. dim_division
2. dim_brand
3. dim_major_category
4. dim_category
5. dim_subcategory
6. dim_product_line
7. dim_sub_product_line
8. dim_sku
9. dim_channel_type
10. dim_market
11. dim_customer_group
12. dim_key_account
13. dim_time
14. dim_version
15. dim_promotion
16. fact_financial_plan (chunked if large)
17. fact_pos_weekly (chunked if large)
18. fact_forecast_snapshot

### Loading behavior
- Use `WRITE_TRUNCATE` disposition (replace table contents on each run)
- Add `loaded_at = CURRENT_TIMESTAMP()` to all fact table rows
- Log progress: print table name, row count before and after load
- Handle chunked CSV files (fact_financial_plan_001.csv, _002.csv etc) by appending
- On error: print full error, skip to next table, log failures
- At end: print summary of successes and failures

### Post-load validation
After all tables loaded, run these queries and print results:
```sql
SELECT 'dim_sku' as tbl, COUNT(*) as rows FROM signal_dw.dim_sku
UNION ALL SELECT 'dim_time', COUNT(*) FROM signal_dw.dim_time
UNION ALL SELECT 'dim_version', COUNT(*) FROM signal_dw.dim_version
UNION ALL SELECT 'fact_financial_plan', COUNT(*) FROM signal_dw.fact_financial_plan
UNION ALL SELECT 'fact_pos_weekly', COUNT(*) FROM signal_dw.fact_pos_weekly
UNION ALL SELECT 'fact_forecast_snapshot', COUNT(*) FROM signal_dw.fact_forecast_snapshot
```

### Computed fields
After loading fact_financial_plan, run an UPDATE equivalent:
```sql
-- Recompute total_forecast_units
UPDATE signal_dw.fact_financial_plan
SET total_forecast_units = stat_forecast_units + promo_uplift_units + manual_override_units,
    total_forecast_dollars = (stat_forecast_units + promo_uplift_units + manual_override_units) * unit_price
WHERE true
```
Note: BigQuery uses MERGE or SELECT INTO for updates — implement accordingly.

### Refresh views
After loading, run CREATE OR REPLACE VIEW for all 4 views defined in TASK_01.

## Create a rerun script
Create `./etl/rerun_etl.sh`:
```bash
#!/bin/bash
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/signal-key.json
python etl/generate_mock_data.py
python etl/load_to_bigquery.py
echo "ETL complete."
```

## Verification Checklist
- [ ] `load_to_bigquery.py` runs without errors
- [ ] dim_sku: 300 rows in BigQuery
- [ ] dim_time: ~2922 rows (2019-2026 daily)
- [ ] dim_version: 16 rows
- [ ] fact_financial_plan: >1M rows
- [ ] fact_pos_weekly: >500K rows
- [ ] fact_forecast_snapshot: >100K rows
- [ ] All 4 views return rows when queried in BigQuery console
- [ ] v_exception_flags returns at least some flagged SKUs
- [ ] Run spot query in BigQuery console:
  ```sql
  SELECT division_name, COUNT(*) as skus
  FROM signal_dw.dim_sku s
  JOIN signal_dw.dim_division d ON s.division_id = d.division_id
  GROUP BY 1
  ```
  Should return 3 divisions with ~100 SKUs each
