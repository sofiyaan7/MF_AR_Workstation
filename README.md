# MF AR Workstation

An internal project portal: one authenticated place from which your team
launches every dashboard, research tool and automation you have built, with
per-employee access control and a complete audit trail.

Projects are **data, not code**. An administrator fills in a short form — name,
URL, description, category, visibility — and the card appears on the dashboard
immediately. No deployment, no source change.

---

## Contents

1. [What it does](#1-what-it-does)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Quick start with Docker](#4-quick-start-with-docker)
5. [Running locally without Docker](#5-running-locally-without-docker)
6. [Environment variables](#6-environment-variables)
7. [Database and migrations](#7-database-and-migrations)
8. [Creating the administrator](#8-creating-the-administrator)
9. [Adding employees](#9-adding-employees)
10. [Adding projects](#10-adding-projects)
11. [Project visibility](#11-project-visibility)
12. [Activity and analytics](#12-activity-and-analytics)
13. [Security model](#13-security-model)
14. [Tests](#14-tests)
15. [API reference](#15-api-reference)
16. [Deployment](#16-deployment)
17. [Known limitations](#17-known-limitations)
18. [Recommended next steps](#18-recommended-next-steps)

---

## 1. What it does

**For an employee**

- Sign in with an Employee ID issued by an administrator.
- See a personalised dashboard: recently opened, favourites, featured, newest.
- Search across project names, descriptions, categories, tags and owners.
- Filter by category, owner, status and tag; sort by name, date or usage.
- Star favourites, review a project's detail page, then launch it.
- Review their own activity history.

**For an administrator**

- Add, edit, duplicate, disable and soft-delete projects.
- Manage the employee register: create, edit, disable, unlock, reset passwords,
  change roles, soft-delete.
- Manage categories.
- Read the full audit trail with filters and CSV export.
- See adoption analytics and per-project usage statistics.

---

## 2. Architecture

```
┌──────────────────────────────────────────────┐
│  PostgreSQL                                  │
│  users · roles · projects · categories       │
│  tags · permissions · favourites             │
│  activity_logs · sessions · login_attempts   │
└──────────────────┬───────────────────────────┘
                   │  SQLAlchemy 2 + Alembic
┌──────────────────▼───────────────────────────┐
│  FastAPI                                     │
│  Argon2id auth · JWT in HttpOnly cookies     │
│  RBAC · visibility rules · audit logging     │
└──────────────────┬───────────────────────────┘
                   │  REST, same-origin, cookie auth
┌──────────────────▼───────────────────────────┐
│  React 18 + TypeScript + Tailwind            │
│  Dashboard · admin panel · analytics         │
└──────────────────────────────────────────────┘
```

Every figure in the UI is computed from the database. Nothing is hardcoded.

**Layout**

```
backend/
  app/
    api/routes/     auth, projects, activity, admin_users, admin_projects, admin_activity
    auth/           authentication and authorization dependencies
    core/           config, security, password policy, logging, middleware, exceptions
    database/       engine, session, declarative base, seed script
    models/         SQLAlchemy models
    schemas/        Pydantic request/response contracts
    services/       auth, project, activity and analytics business logic
    utils/          request context (IP, browser, device), cookie helpers
  alembic/          migrations
  tests/            pytest suite
frontend/
  src/
    components/     ui primitives, layout, project cards, admin dialogs, charts
    hooks/          auth/theme context, React Query hooks
    layouts/        signed-in application shell
    pages/          employee pages + pages/admin
    services/       axios client and typed endpoints
    types/          shared API types
docs/
```

---

## 3. Prerequisites

| Path | Requirements |
|---|---|
| Docker | Docker Engine 24+ with the Compose plugin |
| Local  | Python 3.11+, Node.js 20+, PostgreSQL 14+ |

The backend also runs on Python 3.10 (the test suite is verified there).

---

## 4. Quick start with Docker

```bash
git clone <your-repository-url> mf-ar-workstation
cd mf-ar-workstation

cp .env.example .env
```

Fill in the two required secrets in `.env`:

```bash
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
```

Then start everything:

```bash
docker compose up --build
```

Compose waits for PostgreSQL, applies the migrations, seeds the roles,
categories and the administrator account, and serves the portal at
**http://localhost:8080**.

If you left `FIRST_ADMIN_PASSWORD` blank, the generated password is printed
once in the backend logs:

```bash
docker compose logs backend | grep -A3 "seeding complete"
```

Sign in with that Employee ID and password; the portal will require you to
choose a new password immediately.

To also load sample employees and projects for a demo, set
`SEED_DEMO_DATA=true` in `.env` before the first start.

Useful commands:

```bash
docker compose ps                 # service status
docker compose logs -f backend    # follow API logs
docker compose down               # stop
docker compose down -v            # stop and delete the database volume
```

---

## 5. Running locally without Docker

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env        # set DATABASE_URL and SECRET_KEY

alembic upgrade head
python -m app.database.seed --demo      # omit --demo for a clean install

uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs (disabled when
`ENVIRONMENT=production`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and proxies `/api` to
`http://localhost:8000`, so the browser sees one origin and the authentication
cookies work without any CORS relaxation.

```bash
npm run build     # type-check and produce dist/
npm run lint      # type-check only
```

---

## 6. Environment variables

Full list with comments in [`.env.example`](.env.example).

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection URL | local PostgreSQL |
| `SECRET_KEY` | **Required.** Signs JWTs; rotating it signs everyone out | — |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime | `7` |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Idle timeout before re-authentication | `480` |
| `COOKIE_SECURE` | Send cookies only over HTTPS — **set `true` in production** | `false` |
| `COOKIE_SAMESITE` | `lax`, `strict` or `none` | `lax` |
| `MAX_FAILED_LOGIN_ATTEMPTS` | Failures before the account locks | `5` |
| `ACCOUNT_LOCKOUT_MINUTES` | Lockout duration | `15` |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | Failures per window before throttling | `10` |
| `PASSWORD_MIN_LENGTH` | Minimum password length | `12` |
| `PASSWORD_HISTORY_DEPTH` | Recent passwords that cannot be reused | `5` |
| `FRONTEND_URL` / `CORS_ORIGINS` | Allowed browser origins | localhost |
| `RUN_SEED` / `SEED_DEMO_DATA` | First-run seeding (Docker) | `true` / `false` |
| `FIRST_ADMIN_*` | Bootstrap administrator identity and password | see file |

In production the application refuses to start if `SECRET_KEY` is left at its
development placeholder.

---

## 7. Database and migrations

Thirteen tables with foreign keys and indexes on every column the portal
filters or sorts by — including `users.employee_id`, `projects.category_id`,
and `activity_logs` on `user_id`, `timestamp`, `event_type` and `project_id`.

```bash
cd backend

alembic upgrade head                      # apply
alembic downgrade -1                      # roll back one
alembic current                           # show current revision
alembic history --verbose                 # list revisions
alembic revision --autogenerate -m "add x" # create after a model change
```

Always read a generated migration before applying it.

Schema notes:

- Enum-like columns are `VARCHAR`, so new statuses or roles need no type migration.
- `users` and `projects` carry `is_active` / `is_deleted`; nothing is hard-deleted.
- `activity_logs` denormalises the employee ID, name and project name, so history
  stays readable after a user or project is removed.
- `sessions` stores only the SHA-256 of a refresh token, never the token itself.

---

## 8. Creating the administrator

The administrator password is never hardcoded. Supply it through the
environment, or let the seed script generate one.

```bash
cd backend

# Option A — you choose the password (must satisfy the policy)
FIRST_ADMIN_EMPLOYEE_ID=ADMIN001 \
FIRST_ADMIN_NAME="System Administrator" \
FIRST_ADMIN_EMAIL=admin@yourcompany.com \
FIRST_ADMIN_PASSWORD='<a strong password>' \
python -m app.database.seed

# Option B — let the portal generate one and print it once
python -m app.database.seed
```

The seed is idempotent: if the administrator already exists it is left
untouched. A generated password is flagged `must_change_password`, so the
account must set its own password at first sign-in.

The bootstrap account is a `SUPER_ADMIN`: only that role can create or modify
other administrators.

---

## 9. Adding employees

**Only employees present in the users table can sign in.** There is no
self-registration.

1. Sign in as an administrator.
2. **Admin → Users → Add employee**.
3. Fill in Employee ID, full name, email, department, role and status.
4. Leave the temporary password blank to have a strong one generated.
5. **Create User** — the temporary password is shown **once**. Copy it and
   share it over a secure channel.

The employee signs in with it, is held on the Security page until they set
their own password, and then has full access.

Per-employee actions: edit, view activity, view login history, reset password,
unlock, disable/enable, and soft-delete. You cannot disable or delete your own
account, and a plain `ADMIN` cannot modify a `SUPER_ADMIN`.

---

## 10. Adding projects

This is the core workflow, and it never requires a code change.

1. **Admin → Projects → Add project**.
2. Fill in the form:

   | Field | Notes |
   |---|---|
   | Project name | Shown on the card |
   | Project URL | Any `http(s)` address — Streamlit, React, FastAPI, Voilà, an internal host |
   | Short description | The line on the card |
   | Full description | Shown on the detail page |
   | Category | Drives the quick filters |
   | Tags | Feed search and tag filters |
   | Owner | Displayed and filterable |
   | Icon | Chosen from the icon picker |
   | Status | Active, Maintenance, Deprecated, Coming soon |
   | Visibility | See below |
   | Featured | Pins it to the top of the dashboard |
   | Enabled | Disabled projects are hidden but keep their history |
   | Sort order | Lower appears first |

3. **Add project.** It appears on the dashboard of every employee allowed to
   see it, immediately.

Because the URL is data, the portal is a launcher and makes no assumption about
how a project is built or where it is hosted.

---

## 11. Project visibility

| Visibility | Who can see it |
|---|---|
| `ALL_EMPLOYEES` | Everyone (optionally narrowed to named departments) |
| `SPECIFIC_EMPLOYEES` | Only the Employee IDs you list |
| `ADMIN_ONLY` | Administrators only |

The rule is enforced in the database query for every list, search, favourite
and recents call, and re-checked per object on detail and launch. A project a
user may not see returns `404` rather than `403`, so the API does not confirm
that a hidden project exists. Hiding in the UI is never the mechanism.

---

## 12. Activity and analytics

Every meaningful action is appended to `activity_logs` with the user, Employee
ID, name, event type, description, project, timestamp, IP address, browser, OS,
device, success flag and structured metadata.

Recorded events include `LOGIN`, `LOGOUT`, `FAILED_LOGIN`, `PASSWORD_CHANGED`,
`PASSWORD_RESET`, `PROJECT_VIEWED`, `PROJECT_OPENED`, `PROJECT_FAVOURITED`,
`PROJECT_UNFAVOURITED`, `PROFILE_UPDATED`, `PROJECT_CREATED`, `PROJECT_UPDATED`,
`PROJECT_DELETED`, `USER_CREATED`, `USER_UPDATED`, `USER_DISABLED`,
`USER_ENABLED`, `ROLE_CHANGED` and `UNAUTHORIZED_ACCESS`.

**Admin → Activity Logs** filters by employee, event type, project, date range,
outcome and free text, and exports the filtered set to CSV.

**Admin → Analytics** shows employee and project totals, sign-ins, unique active
users, project opens, failed sign-ins, daily trend charts, ranked project usage,
most active employees and category breakdown. Each project has its own analytics
page with total opens, unique users, favourites, a daily trend and its most
active users.

Employees see only their own history at **My Activity**; the endpoint derives
the user from the session and ignores any identifier sent by the client.

The log is append-only: no route in the application updates or deletes an
activity row, for any role.

---

## 13. Security model

**Authentication.** Argon2id (64 MiB, t=3, p=4). A short-lived access token and
a rotating refresh token are delivered as `HttpOnly` cookies, so no token is
ever readable by JavaScript. Refresh tokens are stored only as a SHA-256 digest
and are rotated on every use, so a captured token dies at the next refresh.

**CSRF.** Double-submit: a readable CSRF cookie must be echoed in the
`X-CSRF-Token` header on every state-changing cookie-authenticated request.

**Brute force.** Failed attempts are recorded and rate-limited per Employee ID
and per IP; the account locks after a configurable number of failures. Login
responses are identical for an unknown Employee ID and a wrong password, and an
unknown ID is still verified against a dummy hash so timing does not reveal
whether the account exists.

**Authorization.** Every protected route resolves the caller from the signed
cookie — never from a header, body field or query parameter. Admin routes are
gated by a dependency that also audits each denial. Disabling or deleting a user
revokes their sessions and invalidates their access token on the next request.

**Data exposure.** No schema anywhere serialises `password_hash`. Application
logs run through a redaction filter that masks anything resembling a password,
hash, token or bearer credential, and request bodies are never logged. Business
audit logs are kept separate from technical logs.

**Other.** Pydantic validation on every input; SQLAlchemy parameter binding
throughout; project URLs restricted to `http`/`https` so a `javascript:` URL can
never reach an anchor; JSON-only responses with `nosniff`; security headers on
API and web tiers; unhandled errors return a generic message with no stack trace.

---

## 14. Tests

```bash
cd backend
source .venv/bin/activate
pytest                       # 145 tests
pytest -v                    # verbose
pytest tests/test_authorization.py
```

The suite runs against a throwaway SQLite database and needs no services.

| File | Covers |
|---|---|
| `test_auth.py` | Sign-in, unknown/invalid credentials, lockout, session rotation, token forgery, password changes and policy, CSRF, headers |
| `test_authorization.py` | Every admin endpoint called by a normal employee, privilege escalation, cross-user activity access, self-disable, live session revocation |
| `test_projects.py` | Project CRUD, all three visibility modes, department restriction, launch tracking, favourites, search, filters, sorting, soft delete |
| `test_admin_users.py` | Employee lifecycle, forced password change, uniqueness, role changes, disable/enable, unlock, password reset, soft delete |
| `test_analytics.py` | Overview figures, time series, per-project stats, audit filters, CSV export |
| `test_categories.py` | Category CRUD, duplicates, in-use protection |
| `test_security.py` | SQL-injection payloads, XSS handling, oversized input, audit-log immutability, log redaction |

Frontend: `npm run build` runs a strict TypeScript check as part of the build.

---

## 15. API reference

All routes are under `/api`. Interactive documentation is at `/docs` outside
production.

**Authentication**

| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/login` | Employee ID + password; sets the session cookies |
| `POST` | `/auth/refresh` | Rotates the refresh token |
| `POST` | `/auth/logout` | Revokes the session |
| `GET` | `/auth/me` | Current profile |
| `PUT` | `/auth/me` | Update own name / email / phone |
| `POST` | `/auth/change-password` | Change own password |
| `GET` | `/auth/password-policy` | Public policy description |
| `POST` | `/auth/forgot-password` | Logs a reset request for admin action |

**Projects** (employee, visibility-filtered)

| Method | Path |
|---|---|
| `GET` | `/projects` — search, filter, sort, paginate |
| `GET` | `/projects/dashboard` |
| `GET` | `/projects/recent`, `/projects/favourites` |
| `GET` | `/projects/categories`, `/projects/tags`, `/projects/owners` |
| `GET` | `/projects/{id}` |
| `POST` | `/projects/{id}/open` |
| `POST` / `DELETE` | `/projects/{id}/favourite` |
| `GET` | `/activity/me` |

**Administration** (all require an admin role)

| Method | Path |
|---|---|
| `GET`/`POST` | `/admin/users` |
| `GET`/`PUT`/`DELETE` | `/admin/users/{id}` |
| `POST` | `/admin/users/{id}/enable`, `/disable`, `/unlock`, `/reset-password` |
| `GET` | `/admin/users/{id}/activity`, `/login-history` |
| `GET`/`POST` | `/admin/projects` |
| `GET`/`PUT`/`DELETE` | `/admin/projects/{id}` |
| `POST` | `/admin/projects/{id}/duplicate`, `/restore` |
| `GET` | `/admin/projects/{id}/stats` |
| `GET`/`POST` | `/admin/categories` |
| `PUT`/`DELETE` | `/admin/categories/{id}` |
| `GET` | `/admin/activity`, `/admin/activity/export`, `/admin/activity/event-types` |
| `GET` | `/admin/login-attempts`, `/admin/analytics`, `/admin/analytics/overview` |

`GET /health` and `GET /api/health` are public and used by the container
health checks.

---

## 16. Deployment

1. **Serve over HTTPS.** Terminate TLS at your reverse proxy or load balancer.
2. **Set `COOKIE_SECURE=true`** and `ENVIRONMENT=production`. The latter also
   disables `/docs` and `/openapi.json`.
3. **Generate fresh secrets** for `SECRET_KEY` and `POSTGRES_PASSWORD`. Never
   reuse development values.
4. **Set `FRONTEND_URL` and `CORS_ORIGINS`** to the real portal hostname.
5. **Forward client IPs.** The bundled nginx sets `X-Forwarded-For` and
   `X-Real-IP`; any proxy in front of it must do the same, or the audit log
   records the proxy's address. The API is started with `--proxy-headers`.
6. **Back up PostgreSQL.** The `postgres_data` volume holds the entire portal,
   including the audit history.
7. **Set `RUN_SEED=false`** after the first successful start.
8. **Keep `SEED_DEMO_DATA=false`** in production.

```bash
docker compose up -d --build
docker compose logs -f backend
```

To upgrade: pull, rebuild, restart. Migrations are applied automatically by the
entrypoint before the API accepts traffic.

---

## 17. Known limitations

- **No email transport.** "Forgot password" records an audited request; an
  administrator issues a temporary password from the admin panel. Wiring up
  SMTP would make it self-service.
- **Rate limiting is per-instance and database-backed.** It is correct for a
  single API container. Running several replicas behind a load balancer would
  benefit from a shared store such as Redis.
- **No SSO.** Authentication is Employee ID and password only. The role table
  and dependency layer are structured so an OIDC or Active Directory provider
  can be added without touching the authorization rules.
- **CSV export is capped** at 10,000 rows per request (50,000 via the `limit`
  parameter) and is generated in memory. A very large export should be moved to
  a streaming or background job.
- **Analytics are computed per request.** At the scale of an internal portal
  this is comfortably fast; with millions of activity rows the daily aggregates
  would be worth materialising.
- **Uploads are not supported.** Project icons are chosen from a fixed set, not
  uploaded.
- **Bundle size.** The admin charts are code-split, but the main bundle is
  around 390 KB (112 KB gzipped). Route-level lazy loading would reduce the
  first paint further.

## 18. Recommended next steps

1. Put the portal behind HTTPS and set `COOKIE_SECURE=true` before rolling it
   out to the team.
2. Add SMTP so password resets and new-account credentials can be delivered
   without a manual hand-off.
3. Add SSO (Microsoft Entra ID or Google Workspace) and map groups to
   departments to keep the employee register in step with HR.
4. Add a project health check: ping each project URL on a schedule and show a
   reachability badge on the card.
5. Add scheduled retention or archival for `activity_logs` once the table grows
   past a few million rows.
6. Consider per-project documentation, comments or ratings — the schema has
   room for them and the service layer is already separated.
