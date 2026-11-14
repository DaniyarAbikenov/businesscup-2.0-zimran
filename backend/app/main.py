import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import reminders
from .cache import get_redis
from .db import SessionLocal
from .errors import ApiError
from .routers import auth, cases, journal, profile

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
for module in (auth, profile, cases, journal):
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
    if request.url.path.startswith("/api") and request.method not in ("GET", "HEAD", "OPTIONS"):
        if "application/json" not in request.headers.get("content-type", ""):
            return JSONResponse({"error": "JSON required"}, status_code=415)
    resp = await call_next(request)
    if request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    get_redis().ping()
    return {"ok": True}
