"""Frontend diagnostics. The browser posts batches of events (errors, failed requests, key user actions);
they are written to the server log (visible with `docker compose logs backend`) and kept in a capped Redis
list so recent client problems can be read without a log stack. No auth: errors can happen before sign-in."""
import json
import logging
import time

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..cache import get_redis
from ..errors import ApiError

router = APIRouter(prefix="/api")
log = logging.getLogger("roleshift.client")
KEEP = 500
PER_MINUTE = 120
LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING, "error": logging.ERROR}


class ClientEvent(BaseModel):
    level: str = "info"
    event: str = Field(max_length=60)
    message: str = Field(default="", max_length=500)
    meta: dict = Field(default_factory=dict)
    at: str = Field(default="", max_length=40)
    path: str = Field(default="", max_length=200)


class Batch(BaseModel):
    events: list[ClientEvent] = Field(max_length=20)


def _trim(meta: dict) -> dict:
    s = json.dumps(meta, default=str)
    return meta if len(s) <= 1000 else {"truncated": s[:1000]}


@router.post("/client-log", status_code=202)
def client_log(body: Batch, request: Request, r=Depends(get_redis)):
    ip = request.client.host if request.client else "?"
    key = f"clientlog:rate:{ip}:{int(time.time() // 60)}"
    n = r.incr(key)
    r.expire(key, 120)
    if n > PER_MINUTE:
        raise ApiError(429, "Too many log events")
    for e in body.events:
        level = e.level if e.level in LEVELS else "info"
        rec = {"level": level, "event": e.event, "message": e.message, "meta": _trim(e.meta), "path": e.path,
               "at": e.at, "ip": ip, "ua": request.headers.get("user-agent", "")[:120]}
        log.log(LEVELS[level], "client %s %s", e.event, json.dumps(rec, default=str))
        r.lpush("clientlog", json.dumps(rec, default=str))
    r.ltrim("clientlog", 0, KEEP - 1)
    return {"accepted": len(body.events)}
