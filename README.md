# RoleShift

A decision workspace for people in their first 90 days of a new position (promotion, new company, new field, new team). The MVP ships one complete flow:

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

Create the test database once, then run the tests (use `python -m pytest`, plain `pytest` does not find the `app` package):

```bash
docker compose exec db createdb -U roleshift roleshift_test
docker compose run --rm -e DATABASE_URL=postgresql+psycopg://roleshift:roleshift@db:5432/roleshift_test \
  -e REDIS_URL=redis://redis:6379/1 backend sh -c "python -m pytest -q"
```

The tests use real Postgres and Redis. They cover the impact calculation, input validation, auth and sessions, login throttling, the full flow through the API, and that one user cannot read another user's case.

## Skills: predict, reveal, grow

For first-time team leads the product is practice for one skill: deciding without fear of a costly mistake. In the three calculators that suit it (priorities, estimate, decision) the person can **guess before the numbers appear** (a few big buttons, always skippable), then the server **scores the guess** against the engine on the same inputs, and the case page shows **"Your guess vs the numbers"** with one friendly sentence and what was not counted.

- **What is guessed and scored** (`app/prediction.py`): priorities, how many tasks finish late in your own order (exact hit) and which order carries the lowest risk (hit); estimate, the date you could safely commit to (error in working days against the safe date: within 1 day is a hit, within 3 is half, more is a miss); decision, which option scores highest (hit). The overall score is 0 to 1. Guesses are validated (types and ranges), stored on the case (`cases.prediction`, `cases.prediction_score`, migration 0009) and never scored in the browser. Change requests have no guess step.
- **Progress, "Your intuition vs the numbers":** per skill (prioritising, estimating, choosing; each scenario carries a `skill` in the pack and shows "Trains: ...") the number of cases, the number of guesses, and the agreement rate with a small bar chart of the last 10. With fewer than 3 guesses it says "Not enough guesses yet" and shows no percentage or trend. The timeline shows "Guess: 1 of 2 right" next to the outcome.
- **What it measures, and what it does not:** agreement with the calculator on your own numbers. It does not measure the quality of decisions in the real world, and the calculator itself is a rule of thumb on what you typed.
- The demo account has eight sample cases with guesses (far off first, closer later), labelled as sample data like the rest of the demo.

## How it works (for users) and vocabulary

The promise: "Facing a decision in a new role? Try your options with your own numbers before you commit, and get a ready message to send." Four steps: describe or pick a scenario, compare options with your numbers, decide and get a ready message, come back and record how it went. The UI says **scenario** (a kind of moment at work), **example** (a scenario with made-up numbers filled in), **option**, **follow-up**; internal words (engine, storyline, preset) stay in code and this README.

- **First use**: a short skippable welcome on Home (remembered in this browser) ending in "Try a worked example", which fills a scenario with an example and goes straight to the result. "How it works" is in the header and footer (`/guide`).
- **Home**: one primary action (describe it in your own words), four recommended scenario cards for your position, then follow-ups due, open cases and your 90-day card. The full catalog and "create a scenario with AI" are collapsed. Navigation: Home, My cases (Journal and Documents as tabs), Progress, Account.
- **Every case** shows four steps (Fill in, Compare, Decide, Follow up), a "Best by the numbers" sentence and a two-sentence "how to read this" above the results, and small "Why we ask" notes on the fields that need one.
- Notes on what was confusing and what changed: `UX_NOTES.md`.

## Progress and email reminders

- **Progress** (`/progress`, `GET /api/progress`): read-only aggregation of existing tables, computed on the server. Day count since signup with 30/60/90 markers, confidence before and after per decided case (SVG chart, average change), decisions timeline with status and the outcome as the user reported it, counts (situations, decisions, follow-ups, documents saved and exported), what was practiced by category, milestones (first situation, decision, debrief), outcome shares, a soft hint after 7 days without a situation, and a "try next" suggestion from the user's role catalog. New users get an empty state with a button to the catalog. A compact card is on Home.
- **Emails are opt-in** (`profiles.email_reminders`, default off; toggle on Progress and Account). A background task (every 10 minutes, guarded by a Redis lock) sends: one "How did it go with <case title>?" email per due follow-up, with three one-click links (worked, partly, did not work yet) that record the outcome through `GET /api/followup/<token>`, and one "Pick your next situation" email 7 days after signup if the user has fewer than 2 situations. Never sent to users who did not opt in, demo users, or twice. Emails contain the case title and links, never the numbers entered. Every email has an unsubscribe link (works without signing in).
- **Tokens**: random, stored hashed (`email_tokens`), outcome links are single use and expire after 30 days; once an outcome is recorded the other links of that case stop working.
- **Settings** (`.env.example`): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `APP_URL` (public address used in links). With `SMTP_HOST` empty the app uses a **log mailer**: the whole email is written to the server log (`docker compose logs backend`) and to the Redis list `outbox` (last 50), nothing is sent. In that mode (or with `TEST_CHECKOUT=true`) the Progress/Account page shows "Send my due reminders now" for testing.
- Limitation: real SMTP delivery has not been tested without credentials; the sending code is plain `smtplib` (STARTTLS, or SSL on port 465).

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
- Migrations: `0001` initial schema, `0002` moves decision, reflection and follow-up out of `cases` and keeps existing data (and reverses it on downgrade), `0003` adds documents and revisions and backfills one Change Request per existing decision, `0004` lets decision option keys come from packs (the database checks the key format, the API checks the key against the situation), `0005` adds `purchases` and `cases.seeded` (demo sample data), `0006` adds `custom_situations`. `backend/tests/test_migrations.py` runs both directions with data on a scratch database.

## How it works

- **Roles and the catalog:** the onboarding offers broad positions (new specialist at a new company, promoted to team lead, head of a function, career switch, four project/delivery manager variants, other). Each situation lists `applies_to` role ids or `"*"`; the Home catalog shows only the matching ones, so `competing-priorities`, `asked-for-a-deadline` and `choose-between-options` are for everyone and `client-change-request` is for the delivery roles and "other". "Describe your situation" and AI-made situations are not limited by `applies_to`: any situation can be opened from the text. Old role ids stay valid.
- **Content packs:** roles, worries and situations are JSON in `backend/app/packs/`. The form, validation, option labels, next steps and pitfalls all come from the pack, so new roles and situations are data. The math for a situation type lives in `backend/app/engine/`.
- **Situations and engines:** each situation in `packs/situations.json` names an engine (`app/engine/__init__.py` registry), its questions (including repeatable rows such as a task list), form groups, option labels, next steps, pitfalls, the document name, and **storylines** (ready examples with filled-in answers, dates given as `{"daysFromNow": n}`). Four engines today: `decision` ("choose between options": 2-5 options scored 1-5 on 2-6 weighted criteria; shows the weighted score out of 100, the ranking, how robust the winner is, the smallest score change and the smallest weight change that would flip it, and four ways to pick: best weighted score, safest, equal weights, only the two heaviest criteria; formulas in `app/engine/decision.py` and in the case's assumptions; the options list takes one score field per criterion, labelled with the criterion names typed so far), `estimate` ("how long will it take, by when?" for any job: PERT three-point estimate and real free hours give four things you could promise, with the chance to make each date; formulas are in `app/engine/estimate.py` and printed in the case's assumptions), `change_request` (accept / defer / decline a late client change) and `priorities` (2-5 competing tasks, compares four orders of work: earliest deadline, most senior requester, biggest consequence, your own order). A new situation on an existing engine is JSON only.
- **Calculation** (`engine/change_request.py`): effort plus overhead, shared across the team (Amdahl-style parallel share), minus schedule buffer gives the slip in working days (weekends skipped). Cost is change work plus team time during the slip plus penalties minus the client share. No LLM involved.
- **Redis:** `sess:*` sessions with TTL, `login:*` throttle counters, `followups:<user>` sorted set that drives the "follow-ups due" badge (rebuilt from Postgres at startup), `hint:*` cache of the AI draft.
- **Create your own situation** (`POST /api/situations/draft`, `POST /api/situations`, `app/presets.py`): for a case that is not in the catalog, the user describes it and the AI (needs `ANTHROPIC_API_KEY`) writes a PRESET on an existing engine. The engine fixes the questions and option keys; the AI may only reword question labels and help, rename the options and write their next steps, write pitfalls and reflection prompts, and propose one example storyline (dates as "+N days"). Code validates all of it: unknown question ids and option keys are dropped, every string is capped, storyline values go through the same per-field validation as the forms, and a missing title or summary is a 422. The user sees a preview ("AI-made, not expert-checked", nothing saved yet), then saves it; saving validates again on the server. Saved situations live in `custom_situations` (max 20 per user, only the owner can see or use them, shown under "My situations" with a delete button) and cases refer to them as `my-<slug>`. Numbers still come only from the engines. 10 AI drafts per user per day; the text is never logged, only its length. The intake returns `noMatch: true` when no keyword matched, and the form then offers "Create a new situation from this text".
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
- Four engines (decision, estimate, change request, priorities), four expert-written situations. The decision calculator only shows what follows from the user's own weights and scores; AI-made presets on it can reword texts but have no storyline with criteria or options. The estimate's chance of making a date is a normal approximation of the PERT estimate, a rule of thumb that depends entirely on the numbers you enter. Users can make more with AI, but those are presets on the same engines and are not expert-checked. A situation with cases cannot be deleted.
- Follow-up reminders appear in the app only (no email or push).
- Outcomes are self-reported and cannot be verified. Risk labels are transparent rules of thumb, not predictions.
- No password reset or email verification.
