import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from resumatch.config import get_settings
from resumatch.db import get_db
from resumatch.models import Login, Pairing, User
from resumatch.schemas import Credentials

DB = Annotated[Session, Depends(get_db)]
COOKIE = "outreach_session"
hasher = PasswordHasher()
dummy = hasher.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require_origin(request: Request):
    settings = get_settings()
    if request.headers.get("origin") not in [settings.web_origin, *settings.web_additional_origins]:
        raise HTTPException(403, f"Open {settings.web_origin}; this request origin is not allowed")


def current_user(request: Request, db: DB):
    token = request.cookies.get(COOKIE, "")
    user = db.scalar(select(User).join(Login).where(
        Login.token_hash == digest(token), Login.expires_at > datetime.now(UTC)
    )) if token and len(token) < 128 else None
    if user is None:
        raise HTTPException(401, "Sign in to continue")
    return user


Owner = Annotated[User, Depends(current_user)]


def browser_owner(request: Request, db: DB):
    token = request.headers.get("authorization", "")
    if not token.startswith("Bearer ") or len(token) > 128:
        raise HTTPException(401, "Pair this browser with your account first")
    pairing = db.scalar(select(Pairing).where(
        Pairing.token_hash == digest(token[7:]), Pairing.revoked.is_(False),
        Pairing.expires_at > datetime.now(UTC),
    ))
    if pairing is None:
        raise HTTPException(401, "Pairing expired or revoked; pair again in the app")
    # Chrome can omit Origin on privileged extension GETs. Require the paired ID
    # header as the credential audience, and reject any conflicting browser Origin.
    origin = request.headers.get("origin")
    if (
        request.headers.get("x-extension-id") != pairing.extension_id
        or (origin is not None and origin != "chrome-extension://" + pairing.extension_id)
    ):
        raise HTTPException(403, "This credential belongs to a different extension")
    return db.get(User, pairing.user_id)


BrowserOwner = Annotated[User, Depends(browser_owner)]
router = APIRouter(prefix="/api/auth")


def user_view(user):
    return {"id": str(user.id), "email": user.email, "weekly_target": user.weekly_target}


def sign_in(db, user, request, response):
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(Login).where(Login.token_hash == digest(old)))
    token = secrets.token_urlsafe(32)
    db.add(Login(token_hash=digest(token), user_id=user.id,
                 expires_at=datetime.now(UTC) + timedelta(days=7)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=604800, httponly=True, samesite="lax",
                        secure=get_settings().cookie_secure, path="/")
    return user_view(user)


@router.post("/register", status_code=201, dependencies=[Depends(require_origin)])
def register(body: Credentials, request: Request, response: Response, db: DB):
    if not get_settings().registration_enabled:
        raise HTTPException(403, "Registration is disabled")
    user = User(email=str(body.email).lower(), password_hash=hasher.hash(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Account already exists; sign in") from None
    return sign_in(db, user, request, response)


@router.post("/login", dependencies=[Depends(require_origin)])
def login(body: Credentials, request: Request, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    try:
        hasher.verify(user.password_hash if user else dummy, body.password)
    except VerificationError:
        raise HTTPException(401, "Email or password is incorrect") from None
    if not user:
        raise HTTPException(401, "Email or password is incorrect")
    return sign_in(db, user, request, response)


@router.get("/me")
def me(user: Owner):
    return user_view(user)


@router.post("/logout", status_code=204, dependencies=[Depends(require_origin)])
def logout(request: Request, response: Response, db: DB):
    db.execute(delete(Login).where(Login.token_hash == digest(request.cookies.get(COOKIE, ""))))
    db.commit()
    response.delete_cookie(COOKIE, path="/")
