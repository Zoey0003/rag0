import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.concurrency import graph_lock
from app.db.session import SessionLocal
from app.modules.auth.dependencies import require_user_id
from app.modules.documents import repository, service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["文档管理"])


def vector_resources():
    # 列表、权限校验不初始化模型；修改操作才连接向量库。
    from pymilvus import MilvusClient
    from utils.env_utils import MILVUS_URI, COLLECTION_NAME

    client = MilvusClient(uri=MILVUS_URI)
    try:
        if not client.has_collection(collection_name=COLLECTION_NAME):
            raise HTTPException(503, "知识库集合不存在，请先初始化集合")
        client.load_collection(collection_name=COLLECTION_NAME)
    except Exception:
        client.close()
        raise
    return client, COLLECTION_NAME


@router.get("")
def list_documents(user_id: UUID = Depends(require_user_id)):
    with SessionLocal() as db:
        return [service.serialize(item) for item in repository.list_documents(db, user_id)]


def ensure_owned(user_id, document_id):
    with SessionLocal() as db:
        if repository.get_owned(db, user_id, document_id) is None:
            raise HTTPException(404, "文档不存在")


def import_upload(file, user_id, document_id=None):
    client = None
    try:
        if document_id is not None:
            ensure_owned(user_id, document_id)
        content = file.file.read(5 * 1024 * 1024 + 1)
        filename = file.filename or ""
        service.decode_upload(filename, content)
        with graph_lock:
            client, collection = vector_resources()
            from documents.markdown_parser import MarkdownParser
            from documents.milvus_db import MilvusVectorSave

            writer = MilvusVectorSave()
            writer.create_connection()
            result = service.upload(SessionLocal, user_id, filename, content,
                                    MarkdownParser(), client, writer, collection, document_id)
        return {**result, "message": "内容未变化，已跳过" if result["status"] == "skipped" else "入库完成"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("个人文档入库失败 user_id=%s document_id=%s", user_id, document_id)
        raise HTTPException(502, "入库失败，可再次上传重试；请通过文档列表确认当前结果") from None
    finally:
        file.file.close()
        if client is not None:
            client.close()


@router.post("/upload")
def upload_document(file: UploadFile = File(...), user_id: UUID = Depends(require_user_id)):
    """当前用户同名文档更新；不同用户同名文件互不影响。"""
    return import_upload(file, user_id)


@router.put("/{document_id}/content")
def update_document(document_id: UUID, file: UploadFile = File(...),
                    user_id: UUID = Depends(require_user_id)):
    return import_upload(file, user_id, document_id)


@router.delete("/{document_id}")
def delete_document(document_id: UUID, user_id: UUID = Depends(require_user_id)):
    ensure_owned(user_id, document_id)
    client = None
    try:
        with graph_lock:
            client, collection = vector_resources()
            return service.delete(SessionLocal, user_id, document_id, client, collection)
    except HTTPException:
        raise
    except Exception:
        logger.exception("个人文档删除失败 user_id=%s document_id=%s", user_id, document_id)
        raise HTTPException(502, "删除未完成，请重试；已进入删除状态的资料不会参与新的检索") from None
    finally:
        if client is not None:
            client.close()
