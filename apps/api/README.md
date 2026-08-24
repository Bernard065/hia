# HIA API (FastAPI)

## Local setup

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env             # then fill in a real JWT_SECRET and DB creds

uvicorn app.main:app --reload
```

API will be up at http://localhost:8000, interactive docs at http://localhost:8000/docs,
health check at http://localhost:8000/health.

Requires a running PostgreSQL instance matching `DATABASE_URL` in `.env` (see
`infrastructure/docker` once the docker-compose file for local Postgres/Redis is added).

## Structure

Each domain from `docs/api/HIA_API_Design.md` gets its own module under `app/modules/`
(auth, patients, reports, laboratory, symptoms, medications, timeline, monitoring, alerts,
insights, assistant, search, rag, safety, audit), each with its own `router.py`. Routers are
wired into the app in `app/main.py` under the `/v1` prefix.
