# Architecture notes

Design decisions that are not obvious from the code, and the reasoning behind
them.

## Projects are data

The single hardest requirement was that new projects must not require a code
change. Everything that distinguishes one project from another — name, URL,
description, category, tags, owner, icon, status, visibility, ordering — is a
column. The frontend renders whatever the API returns.

Two consequences worth knowing:

- **Icons.** An admin picks an icon by name; the value stored is a string such
  as `"BarChart3"`. The frontend maps it through an explicit registry
  (`components/ui/project-icon.tsx`). The registry is deliberate rather than a
  namespace import of the whole icon library: importing everything added about
  750 KB to the bundle. Unknown names fall back to a neutral icon, so a value
  written directly into the database can never break a page.
- **URLs.** Stored verbatim and validated as `http`/`https` only. The portal is
  a launcher and makes no assumption about what is on the other end.

## Authentication: why cookies rather than localStorage

Tokens in `localStorage` are readable by any script on the page, so a single
XSS becomes a full account takeover. Instead:

- The access token and refresh token are `HttpOnly` cookies. JavaScript cannot
  read them.
- Because cookies are sent automatically, CSRF becomes possible, so a
  double-submit token guards every state-changing request: a readable
  `mfar_csrf` cookie must be echoed in the `X-CSRF-Token` header. An attacker's
  page can cause the cookie to be sent but cannot read it to set the header.
- Refresh tokens are stored only as a SHA-256 digest in `sessions`, so a
  database leak does not yield usable tokens, and they rotate on every use — a
  captured token stops working as soon as the real client refreshes.

A `Bearer` header is also accepted, which is what makes the endpoints scriptable
and testable. CSRF checking is skipped for Bearer requests because a browser
never attaches that header automatically, so the attack it defends against
cannot occur.

## Why failed logins commit before raising

`get_db` rolls the request transaction back when an exception propagates. The
audit row for a failed login, and the incremented lockout counter, are written
on exactly that path — so without an explicit commit both would be discarded,
and account lockout would never engage. `record_activity(..., commit=True)` and
the commit inside `auth_service.fail()` exist for that reason. This was caught
by the test suite, not by inspection.

## Visibility is a query filter, not a UI concern

`project_service.visibility_filter()` returns a SQLAlchemy predicate applied to
every project query — lists, search, favourites, recents, tag and owner
lookups. `user_can_access()` mirrors it for single-object checks on detail and
launch. Both live in one module so the two cannot drift apart.

A project the caller may not see returns `404`, not `403`. A `403` would confirm
that the project exists, which is itself a small information leak.

## Append-only audit log

`activity_logs` has no update or delete path anywhere in the application — not
for employees, not for administrators. `test_security.py` asserts this by
inspecting the route table, so adding a `DELETE /activity/...` route in future
would fail the build.

The table denormalises `employee_id`, `user_name` and `project_name`. That is
deliberate duplication: an administrator must still be able to read
*"Employee X opened Project Y on 12 Aug 2026"* after both the employee and the
project have been removed.

## Soft delete everywhere

`users` and `projects` carry `is_active` and `is_deleted`. Deleting a project
hides it from every employee query immediately while preserving referential
integrity for the history. Restoring is a single flag flip. Nothing that would
break the audit trail is ever physically removed.

## Portable types

Enum-like columns are `VARCHAR` rather than native PostgreSQL enums, so adding
a project status or a role is a data change, not a type-altering migration.
Timestamps are `DateTime(timezone=True)` and structured metadata uses the
generic `JSON` type. A side benefit is that the whole test suite runs on SQLite
with no services to start, while production runs on PostgreSQL.

`_day_expr()` in the analytics service truncates a timestamp to `YYYY-MM-DD`
with `substr(cast(...))` for the same reason — it behaves identically on both
engines.

## Timezone handling

Everything is stored and computed in UTC. SQLite returns naive datetimes where
PostgreSQL returns aware ones, so `auth_service._as_utc()` normalises before any
comparison. The frontend formats into the viewer's locale at the edge.

## Frontend state

- **Server state** is React Query. Mutations invalidate the affected keys, so
  adding a project refreshes the admin table and every employee list without
  manual refetching.
- **Session state** is a small context that holds whatever `/auth/me` returned.
  It never holds a token.
- **A single 401 handler** in the axios layer attempts one silent refresh and
  retries the original request; concurrent 401s collapse into one refresh call.
  If that fails, the session is cleared once and the user is told.

Route guards exist for usability — to route people sensibly rather than render
pages that would only 403. They are not a security control; the server re-checks
the caller's role on every request, and `test_authorization.py` calls every
admin endpoint directly as an employee to prove it.

## Design system

One set of CSS custom properties in `index.css` drives the sign-in screen, the
employee dashboard and the admin panel, in both light and dark themes. Charts
read the same `--chart-*` variables, so there is no second palette to keep in
step. Components are hand-written on Radix primitives rather than pulled in via
a generator, so every file in `components/ui` is one the project owns.
