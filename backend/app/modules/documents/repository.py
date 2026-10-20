"""个人文档范围查询，未经登记的共享向量一律不可检索。"""
import hashlib
import json
from uuid import UUID

from sqlalchemy import select, text

from app.modules.documents.models import KnowledgeDocument


def lock_owner(db, owner_id: UUID):
    # 基础同步版本按用户串行写入，覆盖 API 多进程；事务结束自动释放。
    key = int.from_bytes(hashlib.sha256(f"documents:{owner_id}".encode()).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    #pg事务建议锁 

def list_documents(db, owner_id: UUID):
    return list(db.scalars(select(KnowledgeDocument).where(
        KnowledgeDocument.owner_id == owner_id
    ).order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id)))


def get_owned(db, owner_id: UUID, document_id: UUID):
    return db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.id == UUID(str(document_id)),
        KnowledgeDocument.owner_id == owner_id,
    ))#用户和文档查


def get_named(db, owner_id: UUID, filename: str):
    return db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.owner_id == owner_id,
        KnowledgeDocument.filename == filename,
    ))#用户和文件查


def retrieval_expression(db, owner_id: UUID):
    sources = list(db.scalars(select(KnowledgeDocument.active_source).where(
        KnowledgeDocument.owner_id == owner_id,
        KnowledgeDocument.status == "ready",
        KnowledgeDocument.active_source.is_not(None),
    )))
    if not sources:
        return None
    return 'category == "content" and source in ' + json.dumps(sources, ensure_ascii=False)
