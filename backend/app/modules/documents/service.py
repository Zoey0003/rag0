"""同步单文件管理；只发布已完整写入的来源，不改动历史共享数据。"""
import hashlib
import json
import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.modules.documents import repository
from app.modules.documents.models import KnowledgeDocument

logger = logging.getLogger(__name__)


def data_root():
    return Path(os.getenv("KNOWLEDGE_DATA_DIR", str(
        Path(__file__).resolve().parents[4] / "datas" / "personal"
    ))).resolve()


def document_dir(owner_id, document_id):
    return data_root() / str(UUID(str(owner_id))) / str(UUID(str(document_id)))


def decode_upload(filename, content):
    if (not filename or len(filename) > 255 or any(c in filename for c in '/\\:')
            or any(ord(c) < 32 for c in filename) or filename.endswith((" ", "."))
            or Path(filename).suffix.lower() != ".md"):
        raise HTTPException(400, "请选择有效的 .md 文件")
    if not content:
        raise HTTPException(400, "文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "文件不能超过 5 MiB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "文件必须使用 UTF-8 编码") from None
    if not text.strip():
        raise HTTPException(400, "文件没有正文")
    return text.encode("utf-8")


def serialize(record, status=None):
    return {
        "document_id": str(record.id), "filename": record.filename,
        "status": status or record.status, "chunk_count": record.chunk_count,
    }


def source_filter(sources):
    return "source in " + json.dumps(sources, ensure_ascii=False)


def cleanup_sources(paths, client, collection):
    if not paths:
        return
    client.delete(collection_name=collection, filter=source_filter([str(p) for p in paths]))
    rows = client.query(collection_name=collection, filter=source_filter([str(p) for p in paths]),
                        output_fields=["count(*)"], consistency_level="Strong")
    if rows[0]["count(*)"]:
        raise RuntimeError("向量清理尚未完成，请重试")
    for path in paths:
        path.unlink(missing_ok=True)


def upload(session_factory, owner_id, filename, content, parser, client, writer, collection,
           document_id=None):
    content = decode_upload(filename, content)
    digest = hashlib.sha256(content).hexdigest()
    old_source = None
    with session_factory.begin() as db:#开事务
        repository.lock_owner(db, owner_id)#事务业务建议锁 锁用户
        if document_id is None:#上传新文件 就是没传入旧文件的id
            record = repository.get_named(db, owner_id, filename)
        else:#更新旧文件，传入了docid
            record = repository.get_owned(db, owner_id, document_id)
            if record is None:
                raise HTTPException(404, "文档不存在")
            # 按 ID 更新正文，不隐式重命名文档。
            filename = record.filename
        if record is not None and record.status == "deleting":
            raise HTTPException(409, "文档正在删除，请先重试完成删除")
        if record is not None and record.content_hash == digest and record.active_source:
            return serialize(record, "skipped")
        if record is None:
            record = KnowledgeDocument(id=uuid4(), owner_id=owner_id, filename=filename)
            db.add(record)
        folder = document_dir(owner_id, record.id)
        folder.mkdir(parents=True, exist_ok=True)
        candidate = folder / f"{uuid4()}.md"
        candidate.write_bytes(content)
        docs = parser.parse_markdown_to_documents(str(candidate))
        #         '''
        #       举个docs列表的例子  [
        #     Document(
        #         page_content="Redis 可以用来做限流。",
        #         metadata={
        #             "title": "Redis 限流",
        #             "source": "xxx.md",
        #             "filename": "notes.md",
        #             "category": "content",
        #             "category_depth": 1
        #         }
        #     ),

        #     Document(
        #         page_content="PostgreSQL 支持 advisory lock。",
        #         metadata={
        #             "title": "PostgreSQL",
        #             "source": "xxx.md",
        #             "filename": "notes.md",
        #             "category": "content",
        #             "category_depth": 1
        #         }
        #     )
        # ]
        #         '''
        if not docs:
            raise HTTPException(422, "没有解析出正文")
        for doc in docs:
            doc.metadata["source"] = str(candidate)
            doc.metadata["filename"] = filename
            if len(doc.page_content.encode("utf-8")) > 6000:
                raise HTTPException(422, "正文分块超过 6000 字节")
            for key, value in doc.metadata.items():
                if key != "category_depth" and len(str(value).encode("utf-8")) > 1000:
                    raise HTTPException(422, f"{key} 超过 1000 字节")
        writer.add_documents(docs)
        rows = client.query(collection_name=collection,
                            filter=source_filter([str(candidate)]),
                            output_fields=["count(*)"], consistency_level="Strong")
        if rows[0]["count(*)"] != len(docs):
            raise RuntimeError("新文档块数校验失败")
        old_source = record.active_source
        record.active_source = str(candidate)
        record.content_hash = digest
        record.chunk_count = len(docs)
        record.status = "ready"
        db.flush()
        result = serialize(record, "updated")
    # 提交后新来源才可被检索；旧来源清理失败不撤销已发布结果。
    # 失败快照保留供排查；提交结果不确定时不可删除可能已发布的数据。
    if old_source:
        try:
            cleanup_sources([Path(old_source)], client, collection)
        except Exception:
            logger.exception("旧文档来源清理失败 document_id=%s", result["document_id"])
    return result


def delete(session_factory, owner_id, document_id, client, collection):
    # 先提交不可检索状态。外部清理失败时保留记录，允许重复 DELETE。
    with session_factory.begin() as db:
        repository.lock_owner(db, owner_id)
        record = repository.get_owned(db, owner_id, document_id)
        if record is None:
            raise HTTPException(404, "文档不存在")
        record.status = "deleting"
    with session_factory.begin() as db:
        repository.lock_owner(db, owner_id)
        record = repository.get_owned(db, owner_id, document_id)
        if record is None:
            return {"document_id": str(document_id), "status": "deleted"}
        folder = document_dir(owner_id, document_id)
        paths = list(folder.glob("*.md"))
        if record.active_source and Path(record.active_source) not in paths:
            paths.append(Path(record.active_source))
        cleanup_sources(paths, client, collection)
        db.delete(record)
    return {"document_id": str(document_id), "status": "deleted"}
