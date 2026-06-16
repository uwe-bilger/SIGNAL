# TASK_06 — Deploy API to Cloud Run

## Objective
Containerize the FastAPI app and deploy to Cloud Run in GCP project signal-499604.
The deployed API will be the production backend for the React frontend.

## Prerequisites
- TASK_04 complete (API works locally)
- TASK_05 complete (frontend tested against local API)
- Docker installed locally
- gcloud CLI installed and authenticated

## Install and authenticate gcloud
```bash
# If not installed: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud config set project signal-499604
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Step 1 — Create Artifact Registry repository
```bash
gcloud artifacts repositories create signal-api \
  --repository-format=docker \
  --location=us-central1 \
  --description="SIGNAL API container images"
```

## Step 2 — Build and push Docker image
```bash
cd api
docker build -t us-central1-docker.pkg.dev/signal-499604/signal-api/signal-api:latest .
docker push us-central1-docker.pkg.dev/signal-499604/signal-api/signal-api:latest
```

## Step 3 — Deploy to Cloud Run
```bash
gcloud run deploy signal-api \
  --image us-central1-docker.pkg.dev/signal-499604/signal-api/signal-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=signal-499604 \
  --service-account signal-etl@signal-499604.iam.gserviceaccount.com \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 3 \
  --port 8080
```

Note: Cloud Run will use the service account's permissions to access BigQuery.
No need to mount the JSON key — service account auth is automatic on Cloud Run.

## Step 4 — Get the deployed URL
```bash
gcloud run services describe signal-api \
  --region us-central1 \
  --format "value(status.url)"
```
Save this URL — it will look like:
`https://signal-api-xxxxxxxxxxxx-uc.a.run.app`

## Step 5 — Update frontend environment
Update `./frontend/.env.production`:
```
REACT_APP_API_URL=https://signal-api-xxxxxxxxxxxx-uc.a.run.app
```

## Step 6 — Smoke test deployed API
```bash
export API_URL=$(gcloud run services describe signal-api --region us-central1 --format "value(status.url)")
curl $API_URL/health
curl "$API_URL/api/dimensions"
curl "$API_URL/api/plan/summary?fiscal_year=2023&version_id=LE1"
```

## Step 7 — Set up GitHub Actions for auto-deploy (optional but recommended)
Create `.github/workflows/deploy-api.yml`:
```yaml
name: Deploy API to Cloud Run
on:
  push:
    branches: [main]
    paths: ['api/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: signal-api
          region: us-central1
          image: us-central1-docker.pkg.dev/signal-499604/signal-api/signal-api:latest
```
Add `GCP_SA_KEY` secret to GitHub repo (contents of signal-key.json).

## Verification Checklist
- [ ] Artifact Registry repository `signal-api` exists
- [ ] Docker image builds successfully
- [ ] Docker image pushed to Artifact Registry
- [ ] Cloud Run service `signal-api` deployed and status: Ready
- [ ] `curl {API_URL}/health` returns 200
- [ ] `curl {API_URL}/api/dimensions` returns populated data
- [ ] `curl {API_URL}/api/plan/summary?fiscal_year=2023&version_id=LE1` returns data
- [ ] Cloud Run logs show no errors (check in GCP console)
- [ ] `./frontend/.env.production` updated with real Cloud Run URL
