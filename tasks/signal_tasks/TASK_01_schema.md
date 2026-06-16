# TASK_01 — BigQuery Schema

## Objective
Create the BigQuery dataset and all dimension and fact tables for SIGNAL.

## Prerequisites
- `./secrets/signal-key.json` exists
- GCP project `signal-499604` is active
- BigQuery API is enabled

## Environment setup
```bash
pip install google-cloud-bigquery
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/signal-key.json
```

## Step 1 — Create dataset
Create dataset `signal_dw` in project `signal-499604`, location `US`.

## Step 2 — Create dimension tables

### dim_sku
| Column | Type | Description |
|--------|------|-------------|
| sku_id | STRING | Primary key, e.g. SKU-001 |
| sku_name | STRING | Full product name |
| division_id | STRING | FK to dim_division |
| brand_id | STRING | FK to dim_brand |
| product_line_id | STRING | FK to dim_product_line |
| sub_product_line_id | STRING | FK to dim_sub_product_line |
| major_category_id | STRING | FK to dim_major_category |
| category_id | STRING | FK to dim_category |
| subcategory_id | STRING | FK to dim_subcategory |
| unit_cost | FLOAT64 | Standard cost per unit |
| unit_price | FLOAT64 | Standard selling price per unit |
| launch_date | DATE | SKU launch date |
| is_active | BOOL | Currently active SKU |
| is_new_sku | BOOL | No history flag (for M&A tab) |

### dim_division
| Column | Type |
|--------|------|
| division_id | STRING |
| division_name | STRING |

### dim_brand
| Column | Type |
|--------|------|
| brand_id | STRING |
| brand_name | STRING |
| division_id | STRING |

### dim_product_line
| Column | Type |
|--------|------|
| product_line_id | STRING |
| product_line_name | STRING |
| brand_id | STRING |

### dim_sub_product_line
| Column | Type |
|--------|------|
| sub_product_line_id | STRING |
| sub_product_line_name | STRING |
| product_line_id | STRING |

### dim_major_category
| Column | Type |
|--------|------|
| major_category_id | STRING |
| major_category_name | STRING |

### dim_category
| Column | Type |
|--------|------|
| category_id | STRING |
| category_name | STRING |
| major_category_id | STRING |

### dim_subcategory
| Column | Type |
|--------|------|
| subcategory_id | STRING |
| subcategory_name | STRING |
| category_id | STRING |

### dim_channel_type
| Column | Type |
|--------|------|
| channel_type_id | STRING |
| channel_type_name | STRING | Values: Retail, E-commerce, DTC, Distributor |

### dim_market
| Column | Type |
|--------|------|
| market_id | STRING |
| market_name | STRING |
| channel_type_id | STRING |

### dim_customer_group
| Column | Type |
|--------|------|
| customer_group_id | STRING |
| customer_group_name | STRING |
| market_id | STRING |

### dim_key_account
| Column | Type |
|--------|------|
| key_account_id | STRING |
| key_account_name | STRING |
| customer_group_id | STRING |
| channel_type_id | STRING |

### dim_time
| Column | Type | Description |
|--------|------|-------------|
| date_id | DATE | Primary key |
| fiscal_year | INT64 | e.g. 2024 |
| fiscal_quarter | INT64 | 1-4 |
| fiscal_month | INT64 | 1-12 |
| fiscal_week | INT64 | 1-52 |
| fiscal_period_name | STRING | e.g. FY2024-Q1-M01-W01 |
| is_partial_week | BOOL | Week crosses month boundary |
| partial_week_month_split | STRING | e.g. 3d/4d for split weeks |
| calendar_year | INT64 |
| calendar_month | INT64 |
| calendar_week | INT64 |
| day_of_week | INT64 |
| is_weekend | BOOL |
| gregorian_month_name | STRING | e.g. January |
| fiscal_445_pattern | STRING | 4, 4, or 5 week month label |

### dim_version
| Column | Type | Description |
|--------|------|-------------|
| version_id | STRING | Primary key e.g. LE1, LAG3 |
| version_name | STRING | Display name |
| version_type | STRING | Financial or ForecastAccuracy |
| version_order | INT64 | Sort order for display |
| lag_months | INT64 | NULL for financial, 1-10 for lags |

### dim_promotion
| Column | Type |
|--------|------|
| promotion_id | STRING |
| promotion_name | STRING |
| promotion_type | STRING | e.g. TPR, Display, BOGO, Holiday, Launch |
| start_date | DATE |
| end_date | DATE |
| sku_id | STRING |
| key_account_id | STRING |
| expected_lift_pct | FLOAT64 |

## Step 3 — Create fact tables

### fact_financial_plan
Monthly grain. One row per SKU + key_account + time_month + version.

| Column | Type | Description |
|--------|------|-------------|
| record_id | STRING | UUID |
| sku_id | STRING | FK dim_sku |
| key_account_id | STRING | FK dim_key_account |
| fiscal_year | INT64 | |
| fiscal_month | INT64 | |
| version_id | STRING | FK dim_version |
| sell_in_units | FLOAT64 | |
| sell_in_dollars | FLOAT64 | |
| sell_through_units | FLOAT64 | |
| sell_through_dollars | FLOAT64 | |
| corrected_history_units | FLOAT64 | |
| stat_forecast_units | FLOAT64 | |
| manual_override_units | FLOAT64 | Delta, can be negative |
| promo_uplift_units | FLOAT64 | Additive |
| total_forecast_units | FLOAT64 | Computed: stat + promo + override |
| total_forecast_dollars | FLOAT64 | total_forecast_units * unit_price |
| inventory_on_hand_units | FLOAT64 | |
| weeks_of_supply | FLOAT64 | |
| loaded_at | TIMESTAMP | ETL load timestamp |

### fact_pos_weekly
Weekly grain POS and inventory data.

| Column | Type |
|--------|------|
| record_id | STRING |
| sku_id | STRING |
| key_account_id | STRING |
| date_id | DATE |
| fiscal_year | INT64 |
| fiscal_week | INT64 |
| is_partial_week | BOOL |
| pos_units | FLOAT64 |
| pos_dollars | FLOAT64 |
| inventory_on_hand_units | FLOAT64 |
| weeks_of_supply | FLOAT64 |
| loaded_at | TIMESTAMP |

### fact_forecast_snapshot
Lag forecast snapshots for accuracy tracking.

| Column | Type | Description |
|--------|------|-------------|
| record_id | STRING | |
| sku_id | STRING | |
| key_account_id | STRING | |
| fiscal_year | INT64 | Period being forecast |
| fiscal_month | INT64 | Period being forecast |
| version_id | STRING | LAG1 through LAG10 |
| snapshot_date | DATE | When this forecast was made |
| forecast_units | FLOAT64 | What we thought it would be |
| actual_units | FLOAT64 | What actually happened (NULL if future) |
| forecast_error_units | FLOAT64 | actual - forecast |
| forecast_error_pct | FLOAT64 | error / actual |
| loaded_at | TIMESTAMP | |

## Step 4 — Create BigQuery views

### v_demand_plan_summary
Aggregates fact_financial_plan by division, brand, category, channel_type, fiscal_year, fiscal_month, version_id.

### v_forecast_accuracy
Joins fact_forecast_snapshot with dim_version, dim_sku, dim_key_account.
Computes MAPE (mean absolute percentage error) by version and SKU.

### v_pos_monthly
Aggregates fact_pos_weekly to monthly grain for dashboard consumption.

### v_exception_flags
Identifies SKUs where:
- Total forecast > 120% or < 80% of stat forecast (manual override flag)
- Weeks of supply < 4 (stock risk flag)
- Forecast error pct > 20% in last 3 lags (accuracy flag)
- is_new_sku = true (M&A flag)

## Verification Checklist
- [ ] Dataset `signal_dw` exists in project `signal-499604`
- [ ] All 14 dimension tables created with correct schemas
- [ ] All 3 fact tables created with correct schemas
- [ ] All 4 views created and return results (even if empty)
- [ ] Run `SELECT COUNT(*) FROM signal_dw.dim_version` — should return 0 (empty, data comes in TASK_03)
- [ ] No schema errors in BigQuery console
