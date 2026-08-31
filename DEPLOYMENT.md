# Deployment

Production target: **Cloud Run** (the Streamlit app) + **Neon** (Postgres) +
**Secret Manager**, with **Firebase Hosting** as a 301 redirect so
`https://analisador-de-risco.web.app` is a memorable entry point.

Same shape as `alencardoug/ws_plataforma_atendimento_codex`, minus the
separate frontend — Streamlit serves its own UI.

## Why Firebase Hosting is only a redirect

Streamlit needs a WebSocket (`/_stcore/stream`) for all interactivity, and
Firebase Hosting does not proxy WebSocket upgrades through its Cloud Run
rewrites. So Hosting cannot *serve* the app; it issues a `301` to the
`*.run.app` URL. The address bar changes after the redirect — the `.web.app`
URL stays valid as the shareable/bookmark entry point.

## Cost

Expected to stay within free tiers for demo-level traffic:

- **Cloud Run**: free monthly request/compute allotment in `us-east1`
  (Always Free region). Needs a billing account on file even to use the free
  tier. `deploy.sh` sets `--min-instances=0` (scales to zero, no idle
  charge). Set a budget alert during provisioning as a safety net.
- **Neon**: free plan. Compute autosuspends when idle — the app's checkpointer
  uses a pooled connection with pre-ping (`src/dcra/persistence/checkpointer.py`),
  so a suspend/resume is transparent.
- **Firebase Hosting** (Spark plan): no card required.
- **OpenAI API**: unchanged — already billed for local dev; production traffic
  volume is independent of the infra above.

## One-time provisioning (needs your own login — cannot run unattended)

1. Install CLIs: `gcloud` (from cloud.google.com/sdk), and
   `npm i -g firebase-tools`.
2. **GCP project + billing**
   ```bash
   gcloud auth login
   gcloud projects create <PROJECT_ID>          # e.g. analisador-de-risco
   gcloud config set project <PROJECT_ID>
   gcloud billing projects link <PROJECT_ID> --billing-account=<ACCOUNT_ID>
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
     secretmanager.googleapis.com
   ```
   Optional budget alert:
   ```bash
   gcloud billing budgets create --billing-account=<ACCOUNT_ID> \
     --display-name="analisador-de-risco" --budget-amount=5USD \
     --threshold-rule=percent=0.5 --threshold-rule=percent=1.0
   ```
3. **Neon database**
   - Create a project at neon.tech, region **AWS us-east-1 (N. Virginia)**
     (closest of Neon's US regions to `us-east1`).
   - Create a database named `dcra`.
   - Copy the connection string and append `?sslmode=require`. The pooled
     host (`...-pooler...`) is fine — the app already sets
     `prepare_threshold=0`.
4. **Firebase project** — reuse the same GCP project so the Hosting site is
   `analisador-de-risco.web.app`:
   ```bash
   firebase login
   firebase projects:addfirebase <PROJECT_ID>   # if not already a Firebase project
   ```
   `.firebaserc` already pins `analisador-de-risco` as the default project —
   change it there if your project ID differs.

## Deploy

From the repo root, with `gcloud`/`firebase` authenticated and the project set:

```bash
# 1. Secrets (idempotent — re-run to rotate)
export DATABASE_URL='postgresql://…neon.tech/dcra?sslmode=require'
export OPENAI_API_KEY='sk-…'
deploy/create-secrets.sh

# 2. Create the tables in Neon (idempotent)
deploy/init-db.sh

# 2b. (optional) Load 15 synthetic demo cases for a populated table view
DATABASE_URL="$DATABASE_URL" uv run python deploy/seed_demo.py

# 3. Build + deploy the app to Cloud Run
deploy/deploy.sh
#    -> prints the https://dcra-…-ue.a.run.app URL

# 4. Point analisador-de-risco.web.app at that URL (301)
deploy/deploy-hosting.sh
```

Re-deploys are just steps 3 and 4. Step 4 re-reads the live Cloud Run URL each
time, so it is only strictly needed if that URL changed (it normally does not
between deploys of the same service).

## Runtime configuration

`deploy.sh` wires:

| Source | Keys |
|---|---|
| Secret Manager | `DATABASE_URL` = `dcra-database-url`, `OPENAI_API_KEY` = `dcra-openai-api-key` |
| `--set-env-vars` | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`, `DCRA_REVISION_LIMIT=2`, `DCRA_USAGE_VIA_MCP=0`, `LANGSMITH_TRACING=false` |

To enable LangSmith in production, add `LANGSMITH_API_KEY` as a third secret
and flip `LANGSMITH_TRACING=true` in `deploy.sh`.

## Smoke test after deploy

The Cloud Run `/` route returns the Streamlit shell; that alone does not prove
the graph works. After deploying:

1. Open the `*.run.app` URL, click **Começar**.
2. Submit `Remove the column customer_legacy_id from the orders table`.
3. Confirm the counter runs, then that **Evidências**, **Risco: MÉDIO** and a
   Portuguese **Recomendação** render — that exercises the LLM call and both
   DB writes (checkpointer + `analysis_record`).
4. Approve at the review gate; confirm `Registro final: APROVADO`.
5. Reload; open **Reabrir um caso** and check the case shows in the dropdown
   (proves `list_open_cases` reads the checkpointer).

## Not in scope here

Custom domain on Cloud Run, HTTPS load balancer, autoscaling beyond one
instance, high availability, real (non-synthetic) data. Deploying real data
would need the Constitution's synthetic-data article revisited first.
