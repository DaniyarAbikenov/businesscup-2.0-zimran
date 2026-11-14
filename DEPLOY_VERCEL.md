# Deploy on Vercel (one project: static frontend + FastAPI function)

`vercel.json` builds `frontend/` to static files and serves the backend (`api/index.py` -> `backend/app`) as one Python function on the same origin, so the HttpOnly session cookie works. Database: Neon (Postgres). Redis: Upstash. Local `docker compose` development is unchanged.

## 1. Create the project
Vercel -> Add New -> Project -> import the GitHub repo, branch `main`. Leave Framework "Other"; the settings come from `vercel.json`. No domain needed: the `*.vercel.app` URL is used.

## 2. Add the databases (Storage tab, Marketplace)
- **Neon** (Postgres): creates `DATABASE_URL` (also `POSTGRES_URL`, `POSTGRES_URL_NON_POOLING`). The app reads `DATABASE_URL`, then `POSTGRES_URL`, then `POSTGRES_URL_NON_POOLING`, and converts `postgres://` to the psycopg driver itself.
- **Upstash Redis**: creates `KV_URL` / `REDIS_URL` (a `rediss://` TLS address). The app reads `REDIS_URL`, then `KV_URL`, then `UPSTASH_REDIS_URL`. Use the TCP `rediss://` URL, not the REST URL.

## 3. Environment variables (Project -> Settings -> Environment Variables)
| Name | Needed | Value |
|---|---|---|
| `DATABASE_URL` | yes | from the Neon integration |
| `REDIS_URL` | yes | from the Upstash integration (`rediss://...`) |
| `AUTO_MIGRATE` | yes | `true` (creates and updates the tables on cold start, see 4) |
| `CRON_SECRET` | yes | any long random string; Vercel Cron sends it as `Authorization: Bearer ...` |
| `DEMO_MODE` | recommended | `true` (demo button on the sign-in page) |
| `TEST_CHECKOUT` | recommended | `true` (test checkout, no real payments) |
| `ANTHROPIC_API_KEY` | optional | enables AI wording and AI scenarios; empty = the app still works |
| `LLM_MODEL` | optional | default `claude-opus-5-5` |
| `APP_URL` | optional | default is `https://$VERCEL_PROJECT_PRODUCTION_URL` (used in email links) |
| `RESEND_API_KEY` | optional | sends reminder emails through Resend (HTTPS); set `SMTP_FROM` to a sender verified there |
| `SMTP_URL` or `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | optional | plain SMTP instead; with none of these emails are only written to the log |
| `DEMO_PER_HOUR`, `DEMO_KEEP_DAYS`, `PASS_PRICE_CENTS` | optional | defaults 10, 7 and 1900 |

Set automatically on Vercel: `VERCEL=1` (turns on serverless mode: no connection pool, no background loop, `COOKIE_SECURE=true`).

## 4. Migrations: AUTO_MIGRATE
With `AUTO_MIGRATE=true` the function runs `alembic upgrade head` once per cold start, guarded by a Postgres advisory lock so parallel starts do not race (a second run finds nothing to do). If a migration fails the error is logged and the app still serves. The first request after a release that adds a migration is slower. Leave `AUTO_MIGRATE` unset locally.

Manual alternative (needs a database reachable from your computer): `DATABASE_URL='...' scripts/migrate.sh`. Never commit the URL. The demo account needs no seeding: it is created on the first click of the demo button.

## 5. Smoke test
- `https://<project>.vercel.app/health` -> `{"ok": true}` (checks the database and Redis)
- `https://<project>.vercel.app/api/health` -> `{"ok": true}` (touches nothing: point an uptime pinger at this one every 5 minutes to keep the function warm)
- `https://<project>.vercel.app/api/pricing` -> JSON
- Open the site, click the demo button, open an example, make a decision, check Progress, switch the language.
- Cron: Project -> Settings -> Cron Jobs -> run `/api/internal/cron/followups` (404 without the secret, `{"ok": true, ...}` with it).

## Known limits
- **Cold starts**: the first request after idle takes a few seconds.
- **No background jobs**: reminder emails go out once a day (cron, 07:00 UTC, the Hobby limit), not every 10 minutes.
- **Timeout**: functions are limited to 30 s (`maxDuration`).
- **Hobby plan** is for non-commercial use only.
- The Redis reminder index is not rebuilt on start; the daily cron reads Postgres.
