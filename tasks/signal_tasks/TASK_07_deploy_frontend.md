# TASK_07 — Deploy Frontend to Cloudflare Pages

## Objective
Build and deploy the React frontend to Cloudflare Pages,
connected to the production Cloud Run API.
Configure signal.bilger.us to point to the deployment.

## Prerequisites
- TASK_05 complete (frontend works locally)
- TASK_06 complete (API deployed, URL known)
- Cloudflare account exists (bilger.us domain is managed there or via IONOS)
- `./frontend/.env.production` has correct REACT_APP_API_URL

## Step 1 — Cloudflare Pages setup (do this in browser)
1. Go to https://dash.cloudflare.com
2. Click Pages → Create a project → Connect to Git
3. Select GitHub → authorize → choose `uwe-bilger/SIGNAL`
4. Configure build:
   - Project name: `signal`
   - Production branch: `main`
   - Framework preset: Create React App
   - Build command: `npm run build`
   - Build output directory: `build`
   - Root directory: `frontend`
5. Add environment variable:
   - `REACT_APP_API_URL` = your Cloud Run URL
6. Click Save and Deploy

## Step 2 — Configure custom domain
In Cloudflare Pages project settings → Custom domains:
- Add `signal.bilger.us`
- Cloudflare will auto-provision SSL

If bilger.us DNS is managed via IONOS (not Cloudflare):
- In IONOS DNS settings, add CNAME:
  - Name: `signal`
  - Value: `signal.pages.dev` (your Cloudflare Pages default domain)
- DNS propagation: up to 24 hours but usually minutes

## Step 3 — Verify build and deployment
After Cloudflare Pages triggers first build:
- Check build logs for any npm errors
- Verify build output shows all 4 routes
- Check that environment variable is picked up

## Step 4 — Test production deployment
Open https://signal.bilger.us and verify:
- App loads without errors
- Filter dropdowns populate
- All four acts render with real data
- Charts are interactive
- Mobile view works

## Step 5 — Configure automatic deployments
Every push to `main` branch will auto-trigger a new Cloudflare Pages build.
No manual action needed after initial setup.

## Step 6 — Final README
Create `./README.md`:
```markdown
# SIGNAL
Supply Intelligence & Granular Navigation for Agile Lifecycle

A demand planning intelligence platform built as a portfolio demo.

**Live demo:** https://signal.bilger.us

## Stack
- **Data:** BigQuery (GCP project signal-499604)
- **ETL:** Python (google-cloud-bigquery)
- **API:** FastAPI on Cloud Run
- **Frontend:** React + Recharts on Cloudflare Pages

## Local development
# API
cd api && uvicorn main:app --reload

# Frontend
cd frontend && npm start

## Data refresh
./etl/rerun_etl.sh
```

Push README to GitHub:
```bash
git add README.md
git commit -m "docs: add README"
git push
```

## Verification Checklist
- [ ] Cloudflare Pages project created and linked to GitHub
- [ ] First build completes successfully in Cloudflare dashboard
- [ ] https://signal.pages.dev loads the app
- [ ] https://signal.bilger.us resolves (may take up to 24h for DNS)
- [ ] SSL certificate is active (green padlock)
- [ ] All four dashboard acts load with real data
- [ ] Global filters work end-to-end
- [ ] Act 3 lag accuracy chart shows LAG1-LAG10 MAPE
- [ ] Act 4 Hugmoals SKUs all present
- [ ] Mobile view tested at 375px width
- [ ] Push a small change to main branch, verify auto-deploy triggers
- [ ] Share signal.bilger.us URL — it works from any device, no login
