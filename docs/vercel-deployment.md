# Deploying to Vercel

The SPA and the API deploy as **one Vercel project**, which matters: the API
stays same-origin at `/api`, so the HttpOnly auth cookies and the CSRF
double-submit both keep working with no CORS relaxation and no cookie-domain
juggling.

| Piece | How Vercel serves it |
|---|---|
| `frontend/` | Static build, output `frontend/dist` |
| `backend/app/` | Python serverless function via `api/index.py` |
| Database | **External managed Postgres — not in this repo** |

## 1. Provision Postgres

SQLite cannot be used. A serverless filesystem is ephemeral and read-only apart
from `/tmp`, so `backend/mf_ar_workstation.db` would neither persist nor be
shared between invocations. It is excluded from deploys by `.vercelignore`.

Use Vercel Postgres, Neon, or Supabase. You need **two** connection strings:

- **Pooled** (pgbouncer, port 6543 on Supabase / `-pooler` host on Neon) → for `DATABASE_URL`
- **Direct** (port 5432) → for migrations only

Convert the URL to the SQLAlchemy driver form this app expects:

```
postgresql+psycopg2://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

## 2. Apply the schema

```bash
DATABASE_URL='postgresql+psycopg2://…DIRECT…' ./scripts/db-setup.sh --seed
```

Run this from a workstation or CI — **not** at cold start. There is no
serverless equivalent of `backend/docker-entrypoint.sh`, and racing
`alembic upgrade head` across concurrent invocations corrupts migration state.
Re-run it (without `--seed`) after every new migration.

`--seed` creates roles, categories and the bootstrap admin. Set
`FIRST_ADMIN_PASSWORD` beforehand, or leave it blank and copy the strong
password the seeder prints **once**.

Use the *direct* URL here: pgbouncer in transaction mode cannot hold the
advisory locks and DDL that Alembic needs.

## 3. Environment variables

Set these in Vercel → Project → Settings → Environment Variables (Production
*and* Preview). Never commit them.

| Variable | Value | Why |
|---|---|---|
| `DATABASE_URL` | pooled `postgresql+psycopg2://…` | Connection limits |
| `SECRET_KEY` | `python -c "import secrets;print(secrets.token_urlsafe(64))"` | Signs JWTs. Startup **fails** in production if left at the `dev-only` default |
| `ENVIRONMENT` | `production` | Disables `/docs`, `/redoc`, `/openapi.json` |
| `COOKIE_SECURE` | `true` | Cookies HTTPS-only |
| `COOKIE_SAMESITE` | `lax` | Same-origin deploy, so `lax` suffices |
| `FRONTEND_URL` | `https://your-app.vercel.app` | Feeds the CORS allow-list |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Add custom domains, comma-separated |
| `LOG_LEVEL` | `INFO` | Logs go to stdout → Vercel logs |

Optional, first deploy only: `FIRST_ADMIN_EMPLOYEE_ID`, `FIRST_ADMIN_NAME`,
`FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`.

The frontend needs no variables — `VITE_API_URL` defaults to `/api`, which is
correct for a same-origin deploy.

## 4. Deploy

```bash
npm i -g vercel
vercel        # preview
vercel --prod # production
```

This folder is not a git repository. Either deploy with the CLI as above, or
`git init` and push to GitHub for Vercel's git integration.

## 5. Verify

```bash
curl https://your-app.vercel.app/api/health
# {"status":"ok","database":"ok"}
```

`"database":"unavailable"` means `DATABASE_URL` is wrong or the schema is
missing. Then load the site, sign in, and confirm a deep link such as
`/projects` survives a hard refresh (the SPA rewrite).

## Notes and limits

- **`/api/health` is the health check**, not `/health`. Only `/api/*` is routed
  to the function; every other path falls through to the SPA.
- **Cold starts.** The first request after idle pays ~1–2 s to import SQLAlchemy
  and connect. `maxDuration` is 30 s and `memory` 1024 MB in `vercel.json`.
- **Connection pooling** is delegated to pgbouncer. `backend/app/database/session.py`
  switches to SQLAlchemy's `NullPool` when the `VERCEL` env var is present,
  because an in-process pool in a function sandbox holds connections no later
  request can reuse and exhausts the server's connection limit under fan-out.
  Local and Docker runs are unaffected and keep `QueuePool`.
- **Rate limiting and lockout are database-backed** (`login_attempts`), so they
  work correctly across independent function instances. Nothing relies on
  in-process state.
- **Alembic and uvicorn are absent from the root `requirements.txt`** on purpose
  — the function needs neither. `backend/requirements.txt` remains the full
  local/Docker set; keep the two in sync when versions change.
- **Docker is untouched.** `docker-compose.yml` and `start.sh` still work for
  local development; they are just excluded from Vercel uploads.
