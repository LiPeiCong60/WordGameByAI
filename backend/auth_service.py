from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from html import escape

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import AuthToken, CaptchaChallenge, Game, User

PASSWORD_ITERATIONS = 240_000
TOKEN_TTL_DAYS = int(os.getenv("AUTH_TOKEN_TTL_DAYS", "14"))
CAPTCHA_TTL_MINUTES = 10


def _utcnow() -> datetime:
    return datetime.utcnow()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
    }


def _captcha_svg(question: str) -> str:
    escaped = escape(question)
    # Keep the captcha simple and dependency-free; it can be replaced with
    # Turnstile/reCAPTCHA before serious public traffic.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="56" viewBox="0 0 180 56">'
        '<rect width="180" height="56" rx="8" fill="#eef5f7"/>'
        '<path d="M8 42 C42 8, 62 62, 96 25 S148 2, 172 38" stroke="#83a5ad" stroke-width="2" fill="none" opacity=".55"/>'
        '<path d="M16 17 L166 44 M18 44 L162 12" stroke="#bdd1d6" stroke-width="1.5" opacity=".65"/>'
        f'<text x="90" y="35" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="#203141">{escaped}</text>'
        "</svg>"
    )


def create_captcha(db: Session) -> dict:
    left = secrets.randbelow(8) + 2
    right = secrets.randbelow(8) + 2
    answer = str(left + right)
    challenge = CaptchaChallenge(
        id=secrets.token_urlsafe(18),
        answer_hash=_sha256(answer),
        expires_at=_utcnow() + timedelta(minutes=CAPTCHA_TTL_MINUTES),
    )
    db.add(challenge)
    db.commit()
    return {
        "captcha_id": challenge.id,
        "svg": _captcha_svg(f"{left} + {right} = ?"),
        "expires_in": CAPTCHA_TTL_MINUTES * 60,
    }


def verify_captcha(db: Session, captcha_id: str, answer: str) -> None:
    challenge = db.get(CaptchaChallenge, captcha_id)
    if not challenge or challenge.used or challenge.expires_at < _utcnow():
        raise HTTPException(status_code=400, detail="验证码已失效，请刷新后重试。")
    challenge.used = True
    db.add(challenge)
    db.commit()
    if not hmac.compare_digest(challenge.answer_hash, _sha256((answer or "").strip())):
        raise HTTPException(status_code=400, detail="验证码错误。")


def _validate_username(username: str) -> str:
    username = (username or "").strip()
    if not 3 <= len(username) <= 32:
        raise HTTPException(status_code=400, detail="用户名长度需要在 3 到 32 个字符之间。")
    if not all(char.isalnum() or char in "_-" for char in username):
        raise HTTPException(status_code=400, detail="用户名只能包含字母、数字、下划线和短横线。")
    return username


def _validate_password(password: str) -> str:
    if len(password or "") < 8:
        raise HTTPException(status_code=400, detail="密码至少需要 8 位。")
    return password


def register_user(db: Session, username: str, password: str, email: str, captcha_id: str, captcha_answer: str) -> dict:
    verify_captcha(db, captcha_id, captcha_answer)
    username = _validate_username(username)
    password = _validate_password(password)
    existing = db.exec(select(User).where(User.username == username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在。")
    is_first_user = db.exec(select(User)).first() is None
    user = User(
        username=username,
        email=(email or "").strip(),
        password_hash=hash_password(password),
        is_admin=is_first_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return issue_token(db, user)


def issue_token(db: Session, user: User) -> dict:
    raw_token = secrets.token_urlsafe(32)
    token = AuthToken(
        user_id=user.id,
        token_hash=_sha256(raw_token),
        expires_at=_utcnow() + timedelta(days=TOKEN_TTL_DAYS),
    )
    user.last_login_at = _utcnow()
    db.add(token)
    db.add(user)
    db.commit()
    return {
        "token": raw_token,
        "token_type": "bearer",
        "expires_at": token.expires_at.isoformat(),
        "user": public_user(user),
    }


def login_user(db: Session, username: str, password: str) -> dict:
    user = db.exec(select(User).where(User.username == (username or "").strip())).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误。")
    return issue_token(db, user)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录。")
    raw_token = authorization.split(" ", 1)[1].strip()
    token = db.exec(select(AuthToken).where(AuthToken.token_hash == _sha256(raw_token))).first()
    if not token or token.revoked or token.expires_at < _utcnow():
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录。")
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="账号不可用。")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限。")
    return user


def can_access_game(user: User, game: Game) -> bool:
    return user.is_admin or game.owner_user_id == user.id


def require_game_access(db: Session, game_id: int, user: User) -> Game:
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"找不到游戏: {game_id}")
    if not can_access_game(user, game):
        raise HTTPException(status_code=403, detail="无权访问该存档。")
    return game


def require_record_game_access(db: Session, record, user: User) -> Game:
    game_id = getattr(record, "game_id", None)
    if not game_id:
        raise HTTPException(status_code=400, detail="记录没有所属存档。")
    return require_game_access(db, game_id, user)
