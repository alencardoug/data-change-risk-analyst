#!/usr/bin/env bash
# Deploys the Streamlit app to Cloud Run from source. Cloud Build builds the
# repo-root Dockerfile remotely — no local `docker build` needed. Run from the
# repo root.
#
# Prerequisites (one-time — see DEPLOYMENT.md):
#   - gcloud auth login && gcloud config set project <PROJECT_ID>
#   - Run + Cloud Build + Secret Manager APIs enabled
#   - deploy/create-secrets.sh already run (dcra-database-url, dcra-openai-api-key)
#   - deploy/init-db.sh already run against the Neon DATABASE_URL
set -euo pipefail

SERVICE="${SERVICE:-dcra}"
REGION="${REGION:-us-east1}"   # Cloud Run Always Free: us-central1 | us-east1 | us-west1

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=1 \
  --cpu=1 \
  --memory=1Gi \
  --timeout=3600 \
  --set-secrets="DATABASE_URL=dcra-database-url:latest,OPENAI_API_KEY=dcra-openai-api-key:latest" \
  --set-env-vars="LLM_PROVIDER=openai,LLM_MODEL=gpt-4o,DCRA_REVISION_LIMIT=2,DCRA_USAGE_VIA_MCP=0,LANGSMITH_TRACING=false"

echo
echo "Service URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format="value(status.url)"
echo
echo "Next: put that URL into the Firebase redirect -> deploy/deploy-hosting.sh"

# Notes:
# --max-instances=1 keeps Streamlit's per-instance session state coherent
#   without needing --session-affinity. Raise it only together with
#   --session-affinity, or sticky sessions will break mid-interaction.
# --timeout=3600 (the max) keeps Streamlit's long-lived WebSocket from being
#   cut at the default 300s.
# --min-instances=0 => scales to zero when idle (no charge, ~10-20s cold start).
