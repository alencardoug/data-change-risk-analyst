#!/usr/bin/env bash
# One-time (idempotent) Secret Manager setup. Creates/updates the two
# production secrets and grants the Cloud Run runtime service account read
# access. Run once per project, before the first deploy/deploy.sh.
#
# Export these in your shell first — never hardcode them here or commit them:
#   DATABASE_URL    Neon connection string WITH ?sslmode=require, e.g.
#                   postgresql://user:pass@ep-xxx-pooler.<region>.aws.neon.tech/dcra?sslmode=require
#   OPENAI_API_KEY  real OpenAI key (reusing the local dev key is fine)
set -euo pipefail

for var in DATABASE_URL OPENAI_API_KEY; do
  if [ -z "${!var:-}" ]; then
    echo "Missing required env var: $var" >&2
    exit 1
  fi
done

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

upsert dcra-database-url  "$DATABASE_URL"
upsert dcra-openai-api-key "$OPENAI_API_KEY"

PROJECT_NUMBER=$(gcloud projects describe "$(gcloud config get-value project)" \
  --format="value(projectNumber)")
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in dcra-database-url dcra-openai-api-key; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
done

echo "Secrets ready. Read access granted to ${RUNTIME_SA}."
