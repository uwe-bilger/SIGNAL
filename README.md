# SIGNAL

Supply Intelligence & Granular Navigation for Agile Lifecycle

A demand planning intelligence platform built as a portfolio demo for Sr. Manager Demand Planning & S&OP roles.

**Live demo:** https://signal.bilger.us

## What it demonstrates

- **Act 1 — Current State:** Bottoms-up demand plan, SKU × Retailer heatmap, monthly sell-in trend, exception flags
- **Act 2 — Challenger Pack:** Top-down gap analysis waterfall, Budget vs Latest Est by division, manual override drill-down
- **Act 3 — Reconciliation:** Version waterfall (Budget → LE1 → LE2 → LE3 → Latest Est), lag accuracy (MAPE), forecast bias
- **Act 4 — M&A Integration:** New SKU planning for the Hugimals acquisition — comparable analysis, stocking recommendations, supply risk flags

## Stack

| Layer | Technology |
|-------|-----------|
| Data warehouse | BigQuery (`signal-499604.signal_dw`) |
| ETL | Python + pandas + google-cloud-bigquery |
| API | FastAPI on Cloud Run (us-central1) |
| Frontend | React + TypeScript + Recharts + Tailwind CSS |
| Hosting | Cloudflare Pages (signal.bilger.us) |

## Local development

### API
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

### Frontend
```bash
cd frontend
npm install
npm start
```

The frontend reads `REACT_APP_API_URL` from `.env` (defaults to `http://localhost:8080`).

## Data

Mock data covers 163 SKUs across 5 brands, 22 key accounts, 5 channel types, and 7 fiscal years (2020–2026).
Designed to mirror the scale and structure of a ~$200M consumer products company.

### Regenerate data
```bash
./etl/rerun_etl.sh
```

## Deployment

API: Cloud Run via `gcloud run deploy signal-api`
Frontend: Cloudflare Pages (auto-deploys on push to `main`)
