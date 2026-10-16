from uuid import UUID

from fastapi import FastAPI, HTTPException

from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.conversations.router import router as conversations_router
from app.modules.documents.router import router as documents_router
from app.modules.memory.router import router as memory_router


app = FastAPI(title="RAG 问答 API")

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(memory_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health")
def health():
    """仅表示 API 进程已启动，不检查外部依赖。"""
    return {"status": "ok"}


@app.post("/memory/users")
def create_memory_user():
    """停用旧的开发用户创建入口。"""
    raise HTTPException(
        status_code=410,
        detail="此入口已停用，请使用 /auth/register 注册",
    )


@app.get("/memory/users/{user_id}")
def get_memory_user(user_id: UUID):
    """停用凭用户 ID 恢复身份的入口。"""
    raise HTTPException(
        status_code=410,
        detail="此入口已停用，请登录后使用 /auth/me",
    )