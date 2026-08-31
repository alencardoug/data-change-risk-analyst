# Cloud Run production image ONLY.
#
# deploy/deploy.sh runs `gcloud run deploy --source .`, which needs a file
# literally named `Dockerfile` at the build-context root. Local development
# does NOT use this file — it runs `uv run streamlit ...` directly against a
# `docker compose` Postgres (see docker-compose.yml / Makefile).
#
# Keep the Python version in sync with pyproject.toml `requires-python`.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependency layer (cached until the manifest/lock changes). uv.lock is
# .gitignored in this repo, so it may or may not be in the build context —
# the glob tolerates its absence and `uv sync` (no --frozen) resolves fresh
# when it is missing, or honours it when present.
COPY pyproject.toml README.md ./
COPY uv.lock* ./
COPY src ./src
RUN uv sync --no-dev

# Cloud Run injects $PORT (defaults to 8080). Streamlit needs headless mode,
# 0.0.0.0 bind, and its WebSocket works natively over the Cloud Run HTTPS
# front end. XSRF/CORS defaults are fine for a single-origin service.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "streamlit run src/dcra/app/streamlit_app.py --server.port ${PORT} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false"]
