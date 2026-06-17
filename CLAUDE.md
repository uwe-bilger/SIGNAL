# SIGNAL
Supply Intelligence & Granular Navigation for Agile Lifecycle.
FastAPI on Cloud Run → BigQuery (signal_dw) → React on Cloudflare Pages.
GitHub: github.com/uwe-bilger/SIGNAL | Live: signal.bilger.us

## Stack
- GCP project: signal-499604
- BigQuery dataset: signal_dw
- GCS bucket: signal-raw-data
- Service account key: ./secrets/signal-key.json
- API: FastAPI (./api/) → Cloud Run (us-central1)
- Frontend: React + Recharts + Tailwind (./frontend/) → Cloudflare Pages

## Commands
- ETL: `python etl/generate_mock_data.py` then `python etl/load_to_bigquery.py`
- API dev: `cd api && uvicorn main:app --reload --port 8080`
- Frontend dev: `cd frontend && npm start`
- Full redeploy: `bash deploy.sh`
- Lint: `cd frontend && npm run lint`
- Test API: `curl http://localhost:8080/health`

## Git rules
- Never commit directly to main
- Work on feature branches (feat/task-XX-description)
- Merge to main only when task verification checklist is complete
- Pushing a completed feature branch to main to trigger Cloudflare deploy IS allowed
- Never commit ./secrets/ — it is in .gitignore

## Architecture
- ./etl/ — data generation and BigQuery load scripts
- ./api/ — FastAPI app, 7 routers, BigQuery client
- ./frontend/src/pages/ — 4 acts (Act1–Act4)
- ./frontend/src/components/ — shared charts and layout
- Task specs live in TASK_0X_*.md files in repo root

## Key rules
- All data comes from BigQuery — no hardcoded data in frontend
- REACT_APP_API_URL must come from env var, never hardcoded
- CORS is open (*) — this is a public portfolio demo
- secrets/signal-key.json is never committed or logged