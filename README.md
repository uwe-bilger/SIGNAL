# SIGNAL

Supply Intelligence & Granular Navigation for Agile Lifecycle

A demand and supply planning dashboard built for Thermo Fisher's **Filtration and
Separation Division (FSD)**. Serves two purposes: a working analytics tool reflecting
FSD's real planning structure, and a teaching tool with mock data engineered to
demonstrate real planning effects for planner onboarding and training.

**Live:** https://signal.bilger.us

## What it covers

- **Act 1 — Current State:** Bottoms-up demand plan, SKU × Account heatmap, monthly
  sell-in trend, exception flags (stock risk, manual override flags)
- **Act 2 — Challenger Pack:** Top-down gap analysis waterfall, Budget vs Latest Est
  by business line, override drill-down
- **Act 3 — Reconciliation:** Version waterfall (Budget → LE1 → LE2 → LE3 → Latest Est),
  lag accuracy (MAPE), forecast bias by business line
- **Act 4 — FSD Integration:** Acquisition boundary (pre vs. post Sept 2025),
  ERP migration wave timeline per site (SAP → Oracle JDE), data quality step change,
  WFA improving trend (54% → 75% target), new post-TF product SKUs

## Business context

FSD was formed from Thermo Fisher's acquisition of Solventum's Purification &
Filtration business (closed Sept 2025). Three business lines:
Bioprocessing Filtration | Healthcare & Industrial Filtration | Membranes (incl. OEM)

Key planning facts this mock data illustrates:
- WFA baseline: 54%, target 75% within 12 months
- Inventory: ~100 days on hand vs. entitlement of 35–90 days by category
- Demand spikes: COVID sterile filtration (2020), mRNA vaccine (2021), EV battery
  ramp (2022–2024), GLP-1/Ozempic demand pull (2023–2024)
- ERP migration: SAP → JDE site-by-site, each cutover creates a dateable
  data-quality step change (teaching example: real level shift vs. timing artifact)

## Stack

| Layer | Technology |
|-------|------------|
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

Mock data covers ~165 FSD product SKUs across 3 business lines, 22 key accounts
(pharma direct, distributor, OEM, CDMO), 5 manufacturing sites, and 7 fiscal years
(2020–2026). All data points are explainable and traceable to a specific, intentional
planning effect — this is a teaching tool as much as a dashboard.

### Regenerate data
```bash
python etl/generate_mock_data.py    # generates CSVs and uploads to GCS
python etl/load_to_bigquery.py      # loads from GCS into BigQuery
```

## Deployment

API: Cloud Run via `bash deploy.sh` or `gcloud run deploy signal-api`
Frontend: Cloudflare Pages (auto-deploys on push to `main`)
