# TASK_02 — Generate Mock Data

## Objective
Generate all mock data as CSV files and upload to GCS bucket `signal-raw-data`.
Data must mirror real production shapes for all dimensions and facts.

## Prerequisites
- TASK_01 complete
- GCS bucket `signal-raw-data` exists
- `./secrets/signal-key.json` exists

## Environment setup
```bash
pip install google-cloud-storage faker numpy pandas
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/signal-key.json
```

## Output location
All CSVs upload to `gs://signal-raw-data/raw/` with subfolders:
- `gs://signal-raw-data/raw/dimensions/`
- `gs://signal-raw-data/raw/facts/`

Also save locally to `./etl/mock_data/` for inspection.

## Data generation script
Create `./etl/generate_mock_data.py` with the following specifications:

### Divisions (3)
```
DIV-01: Personal Care
DIV-02: Home & Lifestyle
DIV-03: Wellness
```

### Brands (2 per division = 6 total)
```
Personal Care: Lumé, Evara
Home & Lifestyle: Nestly, Bryte
Wellness: Viva, Zerō
```

### Product Lines (2 per brand = 12 total)
Realistic CPG product line names per brand.

### Sub Product Lines (2 per product line = 24 total)

### Categories
```
Major Categories (3): Body, Home, Health
Categories (9): 3 per major
Subcategories (18): 2 per category
```

### SKUs — 300 total
- Distribute evenly across sub product lines and subcategories
- Each SKU gets: realistic name, unit_cost ($2-$45), unit_price ($6-$89)
- 20 SKUs flagged is_new_sku = true (Hugmoals acquisition, no history)
- launch_date between 2018-01-01 and 2024-06-01

### Geography
```
Channel Types (4): Retail, E-commerce, DTC, Distributor

Markets per channel type:
- Retail (5): Northeast, Southeast, Midwest, West, Southwest
- E-commerce (3): Amazon US, Walmart.com, Target.com
- DTC (2): Direct Web, Subscription
- Distributor (2): National Dist A, National Dist B

Customer Groups (2-3 per market = ~24 total)

Key Accounts (3-5 per customer group = ~100 total)
Examples:
- Retail: Target, Walmart, CVS, Walgreens, Kroger, Albertsons, HEB, Publix
- E-commerce: Amazon 1P, Amazon 3P, Walmart.com, Target.com
- DTC: Direct Web Store, Subscribe & Save
- Distributor: UNFI, KeHE, C&S Wholesale
```

### Time dimension
Generate daily rows from 2019-01-01 to 2026-12-31.
Implement 4-4-5 fiscal calendar:
- Fiscal year starts first Monday of February
- Quarters: Q1=4+4+5 weeks, Q2=4+4+5, Q3=4+4+5, Q4=4+4+5
- Flag partial weeks (weeks that cross month boundaries)
- Map each date to fiscal_year, fiscal_quarter, fiscal_month, fiscal_week
- Store gregorian calendar fields alongside fiscal fields

### Versions
```
Financial: BUDGET, OP_PLAN, LE1, LE2, LE3, LATEST_EST
Forecast accuracy: LAG1 through LAG10
```

### Promotions
Generate 8 promotions per year (2020-2026) = ~56 promotions total.
Types: TPR (temporary price reduction), Display, BOGO, Holiday, Launch, Seasonal.
Each promotion tied to 1-3 SKUs and 1-3 key accounts.
Duration: 2-6 weeks.
Expected lift: 15%-45%.

### fact_financial_plan data
Generate monthly rows for:
- All 300 SKUs × ~100 key accounts × 84 months (2020-2026) × 16 versions
- Note: new_sku SKUs only get data from 2024-07 onward
- Base sell-in units: random 50-5000 per SKU/account/month
- Apply realistic seasonality by category (e.g. Wellness peaks Jan, Home peaks Sep-Nov)
- Apply year-over-year growth: 3%-12% depending on division
- LE versions: slight adjustments (+/-5-15%) from Budget
- Lag versions: progressively less accurate further from actual
  (LAG1 within 5% of actual, LAG10 within 25% of actual)
- Promotional uplift: add to months with active promotions
- Manual overrides: random +/-10% on 20% of rows

### fact_pos_weekly data
Generate weekly rows for:
- All 280 active SKUs (exclude new_sku) × ~100 key accounts × 260 weeks (2020-2024)
- POS units ≈ sell-in units with 1-3 week lag and slight variance
- Inventory on hand: 2-8 weeks of supply, fluctuating
- Weeks of supply: computed from inventory / avg weekly POS

### fact_forecast_snapshot data
Generate lag snapshots:
- For each month from 2021-01 to 2024-12 (48 months)
- For each lag 1-10
- snapshot_date = fiscal_month_date minus lag months
- forecast_units = actual with noise: LAG1 ±5%, LAG5 ±15%, LAG10 ±25%
- actual_units = NULL for future months

## File naming convention
```
dimensions/dim_sku.csv
dimensions/dim_division.csv
dimensions/dim_brand.csv
... (one file per dimension table)
facts/fact_financial_plan.csv (may be split: fact_financial_plan_001.csv etc if >500MB)
facts/fact_pos_weekly.csv
facts/fact_forecast_snapshot.csv
```

## Verification Checklist
- [ ] `./etl/generate_mock_data.py` runs without errors
- [ ] All dimension CSVs present in `./etl/mock_data/dimensions/`
- [ ] `dim_sku.csv` has exactly 300 rows
- [ ] `dim_time.csv` has rows from 2019-01-01 to 2026-12-31
- [ ] `dim_version.csv` has exactly 16 rows (6 financial + 10 lags)
- [ ] `dim_promotion.csv` has ~56 rows
- [ ] `fact_financial_plan.csv` has >1M rows
- [ ] `fact_pos_weekly.csv` has >500K rows
- [ ] All files uploaded to `gs://signal-raw-data/raw/`
- [ ] Spot check: open dim_sku.csv, confirm 300 rows, realistic names, prices make sense
- [ ] Spot check: open fact_financial_plan sample, confirm seasonality visible in units
