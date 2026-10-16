import hashlib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.auth.repository import get_token


bearer = HTTPBearer(auto_error=False)


def require_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UUID:
    """校验令牌，并返回当前登录用户 ID。"""
    unauthorized = HTTPException(
        status_code=401,
        detail="未登录或登录已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    access_token = credentials.credentials

    if len(access_token) > 256:
        raise unauthorized

    token_hash = hashlib.sha256(
        access_token.encode("utf-8")
    ).hexdigest()

    with SessionLocal() as db:
        token = get_token(db, token_hash)

        if token is None:
            raise unauthorized

        if token.expires_at <= datetime.now(timezone.utc):
            raise unauthorized

        if db.get(User, token.user_id) is None:
            raise unauthorized

        return token.user_id