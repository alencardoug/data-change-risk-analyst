#!/usr/bin/env bash
# Points analisador-de-risco.web.app at the current Cloud Run URL via a 301
# redirect. Firebase Hosting can't proxy Streamlit's WebSocket, so it is used
# purely as a memorable entry point that redirects to the *.run.app URL.
#
# Reads the live Cloud Run URL and injects it into a throwaway copy of
# firebase.json (the committed one keeps the __CLOUD_RUN_URL__ placeholder so
# it never carries a hash-specific URL). Re-run after any deploy that changes
# the service URL.
#
# Prerequisites:
#   - npm i -g firebase-tools ; firebase login
#   - a Firebase project named `analisador-de-risco` (see .firebaserc / DEPLOYMENT.md)
set -euo pipefail

SERVICE="${SERVICE:-dcra}"
REGION="${REGION:-us-east1}"
FIREBASE_PROJECT="${FIREBASE_PROJECT:-analisador-de-risco}"

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format="value(status.url)")
if [ -z "$URL" ]; then
  echo "Could not read the Cloud Run URL for $SERVICE/$REGION — deploy it first." >&2
  exit 1
fi
echo "Redirect target: $URL"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
sed "s|__CLOUD_RUN_URL__|${URL}|g" firebase.json > "$STAGE/firebase.json"
cp .firebaserc "$STAGE/.firebaserc"
mkdir -p "$STAGE/public"
cp public/index.html "$STAGE/public/index.html"

( cd "$STAGE" && firebase deploy --only hosting --project "$FIREBASE_PROJECT" )

echo
echo "Live: https://${FIREBASE_PROJECT}.web.app  ->  ${URL}"
