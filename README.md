# RoleShift

A decision workspace for people in their first 90 days of a new role. The MVP ships one complete flow:

sign up / sign in -> onboarding (role, context, worries) -> situation "Client changes requirements 2 weeks before release" -> clarifying questions and your project numbers -> **deterministic** impact of Accept / Defer / Decline (new date, cost, risk) -> Change Request document (copy / download) -> debrief and reflection -> progress journal with a "what happened?" follow-up.

## Stack

| Part | Tech |
|---|---|
| Frontend | React 18 + TypeScript + Vite (HMR), plain CSS tokens (no UI kit) |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2 |
| Database | PostgreSQL 16, migrations with Alembic |
| Redis 7 | sessions, login throttle, follow-up reminder index, cache for the optional AI draft |
| Runtime | Docker Compose |

## Run (development, hot reload)

```bash
cp .env.example .env     # optional, every value has a default
docker compose up --build
```

Open http://localhost:5173 (API docs: http://localhost:8000/api/docs).

**Demo:** click **Try the demo** on the sign-in page. It creates a throwaway account (no sign-up) with a finished case (decision, document, reflection, reported outcome), a decision waiting for its follow-up (due now, shown as a badge in the nav) and a draft ready to compare and decide, so every step can be seen in a minute. Turn it off with `DEMO_MODE=false`.

Startup order is enforced by healthchecks: `db` and `redis` -> `migrate` (runs `alembic upgrade head`, then exits) -> `backend` -> `frontend`.

- **Backend hot reload:** `./backend` is bind-mounted and uvicorn runs with `--reload`.
- **Frontend hot reload:** `./frontend` is bind-mounted and Vite serves with HMR. Polling is on so it also works on macOS and Windows.
- Vite proxies `/api` to the backend, so the browser sees one origin and the session cookie just works.
- Data lives in the `pgdata` and `redisdata` volumes. `docker compose down -v` wipes them.

New migration after changing `backend/app/models.py`:

```bash
docker compose run --rm backend alembic revision --autogenerate -m "describe the change"
docker compose up migrate
```

## Tests

```bash
docker compose run --rm -e DATABASE_URL=postgresql+psycopg://roleshift:roleshift@db:5432/roleshift_test \
  -e REDIS_URL=redis://redis:6379/1 backend sh -c "pytest -q"
```

The tests use real Postgres and Redis (create the `roleshift_test` database once: `docker compose exec db createdb -U roleshift roleshift_test`). They cover the impact calculation, input validation, auth and sessions, login throttling, the full flow through the API, and that one user cannot read another user's case.

## Design system

`design/DESIGN.md` defines the visual language ("Ledger"): warm paper neutrals, one ink-teal accent, Fraunces plus Inter, tabular numerals, hairline rules, a comparison table instead of identical cards. Tokens live in `frontend/src/styles/tokens.css`. Read the file before changing UI, and update it when you change the rules.

## Data model

```
users 1--1 profiles
users 1--* cases 1--0..1 decisions        option (accept | defer | decline), rationale, document, follow-up due date
                 1--0..1 reflections      learned, different, confidence_after (1-5)
                 1--0..1 followups        outcome (worked | partly | not_yet | not_applied), notes (self-reported)
                 1--* documents           Change Request (generated, then edited by the user) and client message; 1--* document_revisions keeps every saved version
users 1--* journal   timeline events, optionally linked to a case
```

- `cases` keeps two JSON snapshots: `inputs` (what the user entered) and `result` (what the engine calculated), so an old case never changes when the formulas change. `cases.status` is `draft` until a decision exists.
- Constraints live in the database: allowed options and outcomes, confidence 1 to 5, one decision, reflection and follow-up per case, cascade delete from user to everything.
- Roles and situations are content packs (JSON), not tables.
- Migrations: `0001` initial schema, `0002` moves decision, reflection and follow-up out of `cases` and keeps existing data (and reverses it on downgrade), `0003` adds documents and revisions and backfills one Change Request per existing decision, `0004` lets decision option keys come from packs (the database checks the key format, the API checks the key against the situation), `0005` adds `purchases` and `cases.seeded` (demo sample data). `backend/tests/test_migrations.py` runs both directions with data on a scratch database.

## How it works

- **Content packs:** roles, worries and situations are JSON in `backend/app/packs/`. The form, validation, option labels, next steps and pitfalls all come from the pack, so new roles and situations are data. The math for a situation type lives in `backend/app/engine/`.
- **Situations and engines:** each situation in `packs/situations.json` names an engine (`app/engine/__init__.py` registry), its questions (including repeatable rows such as a task list), form groups, option labels, next steps, pitfalls, the document name, and **storylines** (ready examples with filled-in answers, dates given as `{"daysFromNow": n}`). Two engines today: `change_request` (accept / defer / decline a late client change) and `priorities` (2-5 competing tasks, compares four orders of work: earliest deadline, most senior requester, biggest consequence, your own order). A new situation on an existing engine is JSON only.
- **Calculation** (`engine/change_request.py`): effort plus overhead, shared across the team (Amdahl-style parallel share), minus schedule buffer gives the slip in working days (weekends skipped). Cost is change work plus team time during the slip plus penalties minus the client share. No LLM involved.
- **Redis:** `sess:*` sessions with TTL, `login:*` throttle counters, `followups:<user>` sorted set that drives the "follow-ups due" badge (rebuilt from Postgres at startup), `hint:*` cache of the AI draft.
- **Describe your situation** (`POST /api/intake`, `app/intake.py`): the user writes what is going on in their own words; the app picks the situation and pre-fills the form. Without AI it matches keywords and copies the text into the title and background. With AI the model proposes the situation and the values the person stated; every value then goes through the same validation as the form, one field at a time, and anything invalid is dropped and listed for the user to check. Nothing is saved until the user creates the case. The text itself is never logged (only its length). AI readings are limited to 20 per user per day; over the limit, or if the AI fails, it falls back to keywords.
- **AI (optional):** set `ANTHROPIC_API_KEY` to enable AI reading of descriptions and "Draft a message to the client". Uses the official `anthropic` SDK, model `LLM_MODEL` (default `claude-opus-5-5`) with server-side fallbacks enabled (another model answers if the primary one is overloaded). Without a key those AI options are hidden and nothing else changes. Text is sent to Anthropic only after the user ticks the confidentiality confirmation. AI never computes numbers.
- **Security:** scrypt password hashes, random session tokens (stored hashed) in HttpOnly SameSite cookies, JSON-only writes, per-user ownership checks, login throttling, server-side validation. Set `COOKIE_SECURE=true` behind HTTPS.
- **Privacy:** the UI warns users not to enter confidential employer or client data, and a case cannot be started without ticking a confirmation (also enforced by the API). Users can delete their account and all data (`DELETE /api/account`, page "Account and data"). Copying or downloading the Change Request is recorded as an export event in the journal.

## Pricing

- Free: `FREE_CASES` (default 3) situations of your own. Demo sample cases do not count.
- First 90 Days Pass: `PASS_PRICE_CENTS` (default 2900 = $29), one-time, `PASS_DAYS` (default 90). Buying again extends the pass.
- Checkout is a built-in **test checkout** (`TEST_CHECKOUT=true`): no payment provider, no card details, the purchase is stored with provider `test`. The pricing page (`/pricing`) works without signing in, and starting a situation over the limit leads to it.

## Logs

- Browser: open DevTools, every event is `[roleshift] event - message`. Errors, failed requests and key actions are also posted to `POST /api/client-log`.
- Server: `docker compose logs -f backend` shows one line per API request (`rid=...`, the same id the browser logs) and the client events.
- Nothing the user types is logged, only event names, ids, statuses and timings.

## Limitations

- This compose file is a development stack. For production build the frontend (`npm run build`) and serve `dist/` from a web server or the backend, and run uvicorn without `--reload`.
- AI reading was tested against a fake API in tests and a local stand-in; it has not been run against the real API in this repo.
- Two situations so far (client change request, competing priorities). More are planned on the same engines, plus AI-assisted creation of new situations.
- Follow-up reminders appear in the app only (no email or push).
- Outcomes are self-reported and cannot be verified. Risk labels are transparent rules of thumb, not predictions.
- No password reset or email verification.
