from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .cache import get_redis
from .db import get_db
from .errors import ApiError
from .models import Case, User
from .security import sha

COOKIE = "rs_session"


def current_user(request: Request, db: Session = Depends(get_db), r=Depends(get_redis)) -> User:
    token = request.cookies.get(COOKIE)
    uid = r.get("sess:" + sha(token)) if token else None
    user = db.get(User, int(uid)) if uid else None
    if not user:
        raise ApiError(401, "Not signed in")
    return user


def own_case(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Case:
    c = db.get(Case, case_id)
    if not c or c.user_id != user.id:
        raise ApiError(404, "Not found")
    return c
