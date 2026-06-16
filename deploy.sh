#!/bin/bash
# Run from repo root after: gcloud auth login && gcloud config set project signal-499604
set -e

PROJECT=signal-499604
REGION=us-central1
REPO=signal-api
IMAGE=$REGION-docker.pkg.dev/$PROJECT/$REPO/signal-api:latest
SERVICE=signal-api

echo "==> Creating Artifact Registry repo (if not exists)..."
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT 2>/dev/null || echo "Repo already exists."

echo "==> Building image via Cloud Build (no local Docker needed)..."
gcloud builds submit api/ \
  --tag $IMAGE \
  --project $PROJECT

echo "==> Deploying to Cloud Run..."
gcloud run deploy $SERVICE \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT \
  --service-account signal-etl@$PROJECT.iam.gserviceaccount.com \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 3 \
  --port 8080 \
  --project $PROJECT

echo "==> Getting deployed URL..."
URL=$(gcloud run services describe $SERVICE --region $REGION --project $PROJECT --format "value(status.url)")
echo "API URL: $URL"
echo ""
echo "==> Smoke test..."
curl -s "$URL/health"
echo ""

echo "==> Update frontend/.env.production with:"
echo "REACT_APP_API_URL=$URL"
