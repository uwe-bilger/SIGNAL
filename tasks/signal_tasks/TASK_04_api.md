# TASK_04 — FastAPI Application

## Objective
Build a FastAPI application that reads from BigQuery and serves
structured JSON to the React frontend.

## Prerequisites
- TASK_03 complete (data in BigQuery)
- `./secrets/signal-key.json` exists

## Project structure
```
./api/
├── main.py
├── routers/
│   ├── dimensions.py
│   ├── plan.py
│   ├── pos.py
│   ├── forecast.py
│   ├── exceptions.py
│   └── acquisition.py
├── models/
│   └── schemas.py
├── db/
│   └── bigquery_client.py
├── requirements.txt
└── Dockerfile
```

## Environment setup
```
./api/requirements.txt:
fastapi==0.111.0
uvicorn==0.30.0
google-cloud-bigquery==3.21.0
pydantic==2.7.0
python-dotenv==1.0.1
```

## BigQuery client
Create `./api/db/bigquery_client.py`:
- Initialize client using `GOOGLE_APPLICATION_CREDENTIALS` env var
- Project: `signal-499604`
- Dataset: `signal_dw`
- Helper function: `run_query(sql: str) -> list[dict]`
- Cache results for 5 minutes using functools.lru_cache where appropriate

## API endpoints

### GET /health
Returns `{"status": "ok", "project": "signal-499604"}`

### GET /api/dimensions
Returns all dimension values for filter dropdowns:
```json
{
  "divisions": [...],
  "brands": [...],
  "categories": [...],
  "channel_types": [...],
  "markets": [...],
  "key_accounts": [...],
  "versions": [...],
  "fiscal_years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]
}
```

### GET /api/plan/summary
Query params: division, brand, category, channel_type, key_account, fiscal_year, version_id
Returns monthly sell-in and forecast by SKU aggregated to requested grain.

### GET /api/plan/sku-detail
Query params: sku_id, key_account_id, fiscal_year, version_id
Returns full monthly breakdown for one SKU including all forecast components.

### GET /api/plan/version-compare
Query params: version_a, version_b, fiscal_year, division (optional)
Returns side-by-side comparison of two versions with delta and % change.

### GET /api/pos/weekly
Query params: sku_id (optional), key_account_id (optional), fiscal_year, fiscal_week_start, fiscal_week_end
Returns weekly POS and inventory data.

### GET /api/pos/monthly
Query params: same as weekly but aggregated to month
Returns monthly POS vs sell-in comparison (fill rate view).

### GET /api/forecast/accuracy
Query params: fiscal_year, division (optional), lag_versions (comma separated, e.g. LAG1,LAG3,LAG6)
Returns MAPE and bias by version, useful for lag comparison chart.

### GET /api/forecast/lag-compare
Query params: sku_id, fiscal_year, fiscal_month
Returns all lag versions for a specific period to show forecast evolution.

### GET /api/exceptions
Query params: fiscal_year, fiscal_month (optional), division (optional)
Returns all exception flags from v_exception_flags view:
- override_flag (manual override > 10%)
- stock_risk_flag (WOS < 4)
- accuracy_flag (MAPE > 20% in last 3 lags)
- new_sku_flag (Hugmoals acquisition SKUs)

### GET /api/acquisition/overview
Returns summary of Hugmoals acquisition SKUs:
- Count of new SKUs by division/category
- Supply risk assessment (no history = no baseline)
- Recommended initial stocking quantities based on comparable SKUs
- Timeline flags

### GET /api/reconciliation/summary
Query params: fiscal_year
Returns Budget vs LE1 vs LE2 vs LE3 vs Latest Estimate in one response.
Includes waterfall data (delta between each version).

## CORS configuration
Allow all origins for demo (this is a public portfolio demo):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Local run for testing
```bash
cd api
uvicorn main:app --reload --port 8080
```

## Verification Checklist
- [ ] `uvicorn main:app --reload` starts without errors
- [ ] GET http://localhost:8080/health returns 200
- [ ] GET http://localhost:8080/api/dimensions returns all dropdowns populated
- [ ] GET http://localhost:8080/api/plan/summary?fiscal_year=2023&version_id=LE1 returns data
- [ ] GET http://localhost:8080/api/exceptions?fiscal_year=2024 returns flagged SKUs
- [ ] GET http://localhost:8080/api/acquisition/overview returns Hugmoals SKUs
- [ ] GET http://localhost:8080/api/forecast/accuracy?fiscal_year=2023 returns MAPE data
- [ ] All endpoints return valid JSON with no 500 errors
- [ ] Dockerfile builds successfully: `docker build -t signal-api ./api`
