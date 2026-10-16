import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from memory.database import SessionLocal
from memory.password import hash_password
from memory.repositories.user import (
    create_registered_user,
    get_user_by_username,
)
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from memory.password import verify_password
from memory.repositories.token import create_token
from uuid import UUID

from fastapi import Depends

from memory.authentication import require_user_id
from memory.models import User
from fastapi.security import HTTPAuthorizationCredentials

from memory.authentication import bearer
from memory.repositories.token import delete_token

router = APIRouter(prefix="/auth", tags=["账号认证"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


@router.post("/register", status_code=201)
def register(request: RegisterRequest):
    username = request.username.strip().lower()
    name = request.name.strip()

    if not re.fullmatch(r"[a-z0-9_]{3,64}", username):
        raise HTTPException(
            status_code=422,
            detail="账号需为 3～64 位小写英文字母、数字或下划线",
        )

    if not name:
        raise HTTPException(
            status_code=422,
            detail="显示名称不能为空",
        )

    if not request.password.strip():
        raise HTTPException(
            status_code=422,
            detail="密码不能全为空格",
        )

    # 在开启数据库事务前计算，减少占用连接的时间。
    password_hash = hash_password(request.password)

    try:
        with SessionLocal.begin() as db:
            if get_user_by_username(db, username) is not None:
                raise HTTPException(
                    status_code=409,
                    detail="账号已存在",
                )

            user = create_registered_user(
                db,
                username=username,
                name=name,
                password_hash=password_hash,
            )

            result = {
                "user_id": str(user.id),
                "username": user.username,
                "name": user.name,
            }

        return result

    except IntegrityError:
        # 并发注册时，数据库唯一约束仍能阻止重复账号。
        raise HTTPException(
            status_code=409,
            detail="账号冲突，注册未完成",
        ) from None

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


# 不存在的账号也执行一次密码校验，减少响应耗时差异。
DUMMY_PASSWORD_HASH = hash_password(
    secrets.token_urlsafe(32)
)


@router.post("/login")
def login(request: LoginRequest):
    username = request.username.strip().lower()

    # 查询完成后关闭连接，再执行耗时的密码校验。
    with SessionLocal() as db:
        user = get_user_by_username(db, username)

        user_id = user.id if user else None
        stored_hash = (
            user.password_hash
            if user and user.password_hash
            else DUMMY_PASSWORD_HASH
        )
        user_info = (
            {
                "user_id": str(user.id),
                "username": user.username,
                "name": user.name,
            }
            if user
            else None
        )
        has_credentials = bool(
            user and user.username and user.password_hash
        )

    password_valid = verify_password(
        request.password,
        stored_hash,
    )

    if not password_valid or not has_credentials:
        raise HTTPException(
            status_code=401,
            detail="账号或密码错误",
        )

    # 原始令牌用于客户端请求，哈希用于数据库查询。
    access_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        access_token.encode("utf-8")
    ).hexdigest()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=24)
    )

    with SessionLocal.begin() as db:
        create_token(
            db,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": user_info,
    }

@router.get("/me")
def get_current_user(
    user_id: UUID = Depends(require_user_id),
):#depend执行 `require_user_id()`，把它的返回值给到变量 user_id之后再执行整个函数
    """返回当前登录用户，不返回密码哈希。"""
    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="用户不存在，请重新登录",
            )

        return {
            "user_id": str(user.id),
            "username": user.username,
            "name": user.name,
        }

@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    """撤销当前令牌，重复退出也返回成功。"""
    if credentials is not None:
        token_hash = hashlib.sha256(
            credentials.credentials.encode("utf-8")
        ).hexdigest()

        with SessionLocal.begin() as db:
            delete_token(db, token_hash)

    return {"status": "logged_out"}