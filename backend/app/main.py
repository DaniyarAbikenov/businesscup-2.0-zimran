import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import reminders
from .cache import get_redis
from .db import SessionLocal
from .errors import ApiError
from .routers import auth, billing, cases, intake, journal, profile, telemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("roleshift")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:  # rebuild the Redis reminder index from Postgres
        with SessionLocal() as db:
            reminders.rebuild(db, get_redis())
    except Exception as e:  # e.g. DB not migrated yet: the app can still start
        log.warning("reminder index rebuild skipped: %s", e)
    yield


app = FastAPI(title="RoleShift API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
for module in (auth, profile, cases, journal, telemetry, billing, intake):
    app.include_router(module.router)


@app.exception_handler(ApiError)
async def api_error(request: Request, e: ApiError):
    body = {"error": e.message}
    if e.fields:
        body["fields"] = e.fields
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
