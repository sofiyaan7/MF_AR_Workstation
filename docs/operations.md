# Operations runbook

Day-to-day tasks for whoever runs the portal.

## Health

```bash
curl -fsS http://localhost:8080/healthz          # web tier
curl -fsS http://localhost:8000/api/health       # API + database
```

`/api/health` reports `{"status": "degraded", "database": "unavailable"}` if the
API is up but cannot reach PostgreSQL.

## An employee cannot sign in

Check in this order:

1. **Do they exist?** Admin → Users, search their Employee ID. If it is absent
   they were never added; there is no self-registration.
2. **Locked?** The status column shows `Locked` after too many failed attempts.
   Use **Unlock account**. Lockout also clears itself after
   `ACCOUNT_LOCKOUT_MINUTES`.
3. **Disabled or deleted?** Status `Disabled`, or the row only appears with
   *Show deleted*. Use **Enable**.
4. **Forgotten password?** Use **Reset password** and share the one-time value
   securely. It is displayed once and cannot be retrieved afterwards.
5. **Still failing?** Admin → Activity Logs, filter by their Employee ID and
   event type `FAILED_LOGIN`. The `failure_reason` distinguishes
   `bad_password`, `unknown_employee_id`, `account_disabled` and
   `account_locked`.

## An employee cannot see a project

Almost always visibility. Open the project in Admin → Projects:

- `ADMIN_ONLY` — invisible to standard employees by design.
- `SPECIFIC_EMPLOYEES` — their Employee ID must be in the list. IDs that did not
  match a user were ignored at save time; re-add and check the spelling.
- `ALL_EMPLOYEES` with departments set — their department must match exactly.
- Status `COMING_SOON` — visible but deliberately not launchable.
- Disabled or deleted — hidden from employees entirely.

## Answering an audit question

Admin → Activity Logs, then filter:

| Question | Filter |
|---|---|
| Who signed in today? | Event type `LOGIN`, From = today |
| What did one employee do? | Employee ID = theirs |
| Who opened a project? | Search the project name, event type `PROJECT_OPENED` |
| Which sign-ins failed? | Event type `FAILED_LOGIN`, or Outcome = Failed |
| Who created or changed a project? | Event type `PROJECT_CREATED` / `PROJECT_UPDATED` |
| Who disabled an employee? | Event type `USER_DISABLED` |
| When did someone change their password? | Event type `PASSWORD_CHANGED` |
| What happened in a time window? | From / To |

**Export CSV** exports exactly the filtered set.

Per-employee history is also available directly from Admin → Users → *View
activity* / *Login history*.

## Backups

Everything, including the audit trail, lives in PostgreSQL.

```bash
# Back up
docker compose exec -T postgres pg_dump -U portal mf_ar_workstation \
  | gzip > backup-$(date +%F).sql.gz

# Restore into an empty database
gunzip -c backup-2026-08-26.sql.gz \
  | docker compose exec -T postgres psql -U portal -d mf_ar_workstation
```

Schedule this daily and keep the backups off the portal host.

## Upgrades

```bash
git pull
docker compose up -d --build
docker compose logs -f backend
```

The entrypoint applies pending migrations before the API serves traffic. Take a
backup first if the release contains a migration.

## Rotating the signing key

Changing `SECRET_KEY` invalidates every issued token, signing all users out
immediately. That is the intended way to respond to a suspected token leak.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# update SECRET_KEY in .env
docker compose up -d backend
```

## Log hygiene

Two separate streams:

- **Application logs** (stdout) — technical: request lines, warnings, stack
  traces. A redaction filter masks anything resembling a password, hash or
  token, and request bodies are never logged.
- **Business audit log** (`activity_logs`) — who did what, kept indefinitely.

Never add a log statement that prints a request body on an auth route.

## Growth

At internal-portal scale the queries are indexed and fast. Watch two things:

- `activity_logs` row count. Past a few million rows, consider archiving older
  partitions and materialising the daily aggregates the analytics page computes
  per request.
- CSV exports. They are built in memory and capped at 50,000 rows; a larger
  export should become a background job.
