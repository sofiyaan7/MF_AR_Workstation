# Deploying to Vercel

The SPA and the API deploy as **one Vercel project** using
[Services](https://vercel.com/docs/services) — Vercel's supported way to run a
JS frontend and a Python backend from one repository. Each service builds
independently and they share one domain, which matters here: the API stays
same-origin at `/api`, so the HttpOnly auth cookies and the CSRF double-submit
work with no CORS relaxation and no cookie-domain juggling.

| Service | Root | How it builds |
|---|---|---|
| `frontend` | `frontend/` | Vite preset → static `dist/`, SPA fallback to `index.html` |
| `backend` | `backend/` | FastAPI preset, entrypoint `app.main:app` |
| Database | — | **External managed Postgres, not in this repo** |

Top-level rewrites are the public ingress: `/api/(.*)` enters the backend and
everything else enters the frontend. A service receives the **original** path,
so `/api/auth/login` arrives at FastAPI as `/api/auth/login`, matching the
app's `API_PREFIX`. No app-side path rewriting is needed.

> Routing into a service is final. If nothing matches inside it, Vercel returns
> that service's 404 rather than falling through to the other service.

## 1. Provision Postgres

SQLite cannot be used. The serverless filesystem is ephemeral and read-only
apart from `/tmp`, so `backend/mf_ar_workstation.db` would neither persist nor
be shared between invocations. It is excluded from deploys by `.vercelignore`.

Use Vercel Postgres, Neon, or Supabase. You need **two** connection strings:

- **Pooled** (pgbouncer — port 6543 on Supabase, `-pooler` host on Neon) → `DATABASE_URL`
- **Direct** (port 5432) → migrations only

Convert to the SQLAlchemy driver form this app expects:

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

Push to `main` and let Vercel's GitHub integration build, or use the CLI:

```bash
npm i -g vercel
vercel        # preview
vercel --prod # production
```

`vercel dev` runs both services together locally the way production wires them.

## 5. Verify

```bash
curl https://your-app.vercel.app/api/health
# {"status":"ok","database":"ok"}
```

`"database":"unavailable"` means `DATABASE_URL` is wrong or the schema is
missing. Then load the site, sign in, and confirm a deep link such as
`/projects` survives a hard refresh (the frontend SPA fallback).

## Notes and limits

- **`/api/health` is the health check**, not `/health`. Only `/api/*` enters the
  backend service; every other path goes to the frontend.
- **Do not add a `requirements.txt` or a Python entrypoint at the repository
  root.** Vercel detects Python frameworks from dependency files, and a
  detected framework preset takes precedence over everything else — it would
  capture all requests and bypass the frontend build. Backend dependencies
  belong in `backend/requirements.txt`, inside the service root. This is what
  broke the first deployment attempt.
- **Python is pinned to 3.12** via `backend/.python-version` (Vercel's default;
  3.13 and 3.14 are also available).
- **Connection pooling** is delegated to pgbouncer.
  `backend/app/database/session.py` switches to SQLAlchemy's `NullPool` when the
  `VERCEL` env var is present, because an in-process pool in a serverless
  sandbox holds connections no later request can reuse and exhausts the
  server's connection limit under fan-out. Local and Docker runs keep
  `QueuePool`.
- **Rate limiting and lockout are database-backed** (`login_attempts`), so they
  behave correctly across independent instances. Nothing relies on in-process
  state.
- **Cold starts.** The first request after idle pays ~1–2 s to import
  SQLAlchemy and connect.
- **Dockerfiles are excluded** by `.vercelignore`. Left in the upload, a
  `Dockerfile` in a service root can make Vercel build that service as a
  container instead of a function.
- **Docker and `start.sh` are untouched** for local development; they are just
  excluded from Vercel uploads.
