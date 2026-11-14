import re
import secrets

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config, llm
from ..cache import get_redis
from ..db import get_db
from ..deps import COOKIE, current_user
from ..errors import ApiError
from ..models import Profile, User
from ..packs import public_pack
from ..security import check_password, hash_password, sha

router = APIRouter(prefix="/api")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = ""
    password: str = ""


def start_session(response: Response, r, user_id: int):
    token = secrets.token_hex(32)
    r.set("sess:" + sha(token), user_id, ex=config.SESSION_DAYS * 86400)
    response.set_cookie(COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/")


@router.post("/auth/register", status_code=201)
def register(body: Credentials, response: Response, db: Session = Depends(get_db), r=Depends(get_redis)):
    email = body.email.strip().lower()
    if not EMAIL.match(email) or len(email) > 200:
        raise ApiError(400, "Enter a valid email")
    if not 8 <= len(body.password) <= 200:
        raise ApiError(400, "Password must be 8 to 200 characters")
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "This email is already registered")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    start_session(response, r, user.id)
    return {"ok": True}


@router.post("/auth/login")
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db), r=Depends(get_redis)):
    email = body.email.strip().lower()
    key = f"login:{email}|{request.client.host if request.client else ''}"
    if int(r.get(key) or 0) >= 10:
        raise ApiError(429, "Too many attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == email))
    if not user or not check_password(body.password, user.password_hash):
        r.incr(key)
        r.expire(key, 900)
        raise ApiError(401, "Wrong email or password")
    r.delete(key)
    start_session(response, r, user.id)
    return {"ok": True}


@router.post("/auth/logout")
def logout(request: Request, response: Response, r=Depends(get_redis)):
    token = request.cookies.get(COOKIE)
    if token:
        r.delete("sess:" + sha(token))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def profile_dict(p: Profile | None):
    return None if not p else {"roleId": p.role_id, "industry": p.industry, "tenure": p.tenure, "fears": p.fears, "fearNote": p.fear_note}


@router.get("/me")
def me(user=Depends(current_user), db: Session = Depends(get_db)):
    return {"user": {"id": user.id, "email": user.email}, "profile": profile_dict(db.get(Profile, user.id)), "llmEnabled": llm.enabled()}


@router.get("/packs")
def packs(user=Depends(current_user)):
    return public_pack()
