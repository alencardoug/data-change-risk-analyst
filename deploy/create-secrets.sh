#!/usr/bin/env bash
# One-time (idempotent) Secret Manager setup. Creates/updates the production
# secrets and grants the Cloud Run runtime service account read access. Run once
# per project, before the first deploy/deploy.sh; re-run to rotate.
#
# Export the values in your shell first — never hardcode them here or commit them:
#   DATABASE_URL       Neon connection string WITH ?sslmode=require, e.g.
#                      postgresql://user:pass@ep-xxx-pooler.<region>.aws.neon.tech/dcra?sslmode=require
#   OPENAI_API_KEY     real OpenAI key (reusing the local dev key is fine)
#   LANGSMITH_API_KEY  LangSmith key (deploy.sh enables tracing into project dcra-prod;
#                      reusing the local dev key is fine)
#
# Only the variables you export are written. A secret whose variable is not
# exported is left untouched if it already exists, and is an error if it does
# not — so adding one secret later never overwrites the others (e.g. with a
# local DATABASE_URL sourced from .env by mistake).
set -euo pipefail

gcloud services enable secretmanager.googleapis.com

upsert() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
  else
    printf '%s' "$value" | gcloud secrets create "$name" \
      --data-file=- --replication-policy=automatic
  fi
}

sync() {
  local name="$1" var="$2"
  if [ -n "${!var:-}" ]; then
    upsert "$name" "${!var}"
    echo "$name: written from \$$var"
  elif gcloud secrets describe "$name" >/dev/null 2>&1; then
    echo "$name: kept (\$$var not exported)"
  else
    echo "$name: missing and \$$var not exported" >&2
    exit 1
  fi
}

sync dcra-database-url     DATABASE_URL
sync dcra-openai-api-key   OPENAI_API_KEY
sync dcra-langsmith-api-key LANGSMITH_API_KEY

PROJECT_NUMBER=$(gcloud projects describe "$(gcloud config get-value project)" \
  --format="value(projectNumber)")
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in dcra-database-url dcra-openai-api-key dcra-langsmith-api-key; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
done

echo "Secrets ready. Read access granted to ${RUNTIME_SA}."
