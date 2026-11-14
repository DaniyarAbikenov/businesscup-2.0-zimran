import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from starlette.concurrency import run_in_threadpool

from . import config, i18n, msg, reminders
from .cache import get_redis
from .db import SessionLocal
from .errors import ApiError
from .routers import auth, billing, cases, intake, journal, profile, progress, situations, telemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("roleshift")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.ON_VERCEL:  # serverless: no startup work and no background loop; reminders run from the daily cron endpoint
        yield
        return
    try:  # rebuild the Redis reminder index from Postgres
        with SessionLocal() as db:
            reminders.rebuild(db, get_redis())
    except Exception as e:  # e.g. DB not migrated yet: the app can still start
        log.warning("reminder index rebuild skipped: %s", e)
    task = asyncio.create_task(progress.reminder_loop())
    yield
    task.cancel()


app = FastAPI(title="RoleShift API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
for module in (auth, profile, cases, journal, telemetry, billing, intake, situations, progress):
    app.include_router(module.router)


def profile_of(request: Request):
    """The signed-in user's (position, language), cached in Redis and refreshed whenever the profile or the language is saved."""
    import json as _json
    from .deps import COOKIE
    from .models import Profile
    from .security import sha
    token = request.cookies.get(COOKIE)
    if not token:
        return None, None
    r = get_redis()
    uid = r.get("sess:" + sha(token))
    if not uid:
        return None, None
    cached = r.get(f"prof:{uid}")
    if cached is not None:
        d = _json.loads(cached)
        return d.get("role"), d.get("language")
    with SessionLocal() as db:
        p = db.get(Profile, int(uid))
        d = {"role": p.role_id if p else None, "language": p.language if p else None}
    r.set(f"prof:{uid}", _json.dumps(d), ex=86400)
    return d["role"], d["language"]


@app.exception_handler(ApiError)
async def api_error(request: Request, e: ApiError):
    body = {"error": msg.tr(e.message)}
    if e.fields:
        body["fields"] = {k: msg.tr(v) for k, v in e.fields.items()}
    return JSONResponse(body, status_code=e.status)


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, e: RequestValidationError):
    return JSONResponse({"error": "Invalid request"}, status_code=400)


@app.middleware("http")
async def api_rules(request: Request, call_next):
    # Writes must be JSON: blocks plain cross-site form posts. API responses are never cached.
    # Every API request gets an id (returned as X-Request-ID, shown by the frontend log) and one log line.
    path = request.url.path
    is_api = path.startswith("/api")
    rid = request.headers.get("x-request-id", "")[:40] or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    role, saved = await run_in_threadpool(profile_of, request)  # a context variable set in a dependency would not reach the endpoint's thread
    msg.set_lang(i18n.resolve(request, type("P", (), {"language": saved})()))  # the language of this request: header or ?lang=, then the saved choice, then Accept-Language
    msg.set_role(role)  # the position's vocabulary
    if is_api and request.method not in ("GET", "HEAD", "OPTIONS") and "application/json" not in request.headers.get("content-type", ""):
        resp = JSONResponse({"error": "JSON required"}, status_code=415)
    else:
        try:
            resp = await call_next(request)
        except Exception:
            log.exception("unhandled error rid=%s %s %s", rid, request.method, path)
            resp = JSONResponse({"error": "Something went wrong on our side. Try again."}, status_code=500)
    if is_api:
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Request-ID"] = rid
        if path != "/api/client-log":
            log.info("api rid=%s %s %s -> %s %.0fms", rid, request.method, path, resp.status_code, (time.perf_counter() - started) * 1000)
    return resp


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    get_redis().ping()
    return {"ok": True}
