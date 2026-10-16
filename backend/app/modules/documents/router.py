from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from pymilvus import MilvusClient

from app.core.concurrency import graph_lock
from app.modules.auth.dependencies import require_user_id

from documents.incremental_import import DATA_DIR, import_one_file
from documents.markdown_parser import MarkdownParser
from documents.milvus_db import MilvusVectorSave
from utils.env_utils import MILVUS_URI, COLLECTION_NAME


router = APIRouter(
    prefix="/documents",
    tags=["文档管理"],
)


@router.post("/upload")
def upload_document(file: UploadFile = File(...),
                    user_id:UUID=Depends(require_user_id)):
    filename = file.filename or ""

    # 仅接受当前目录中的单个 Markdown 文件名。
    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or ":" in filename
        or filename.endswith((" ", "."))
        or Path(filename).suffix.lower() != ".md"
    ):
        raise HTTPException(status_code=400, detail="请选择有效的 .md 文件")

    try:
        content = file.file.read(5 * 1024 * 1024 + 1)
    finally:
        file.file.close()

    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件不能超过 5 MiB")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="文件必须使用 UTF-8 编码",
        ) from None

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件没有正文")

    client = None
    try:
        # 与问答共用锁，避免替换资料期间执行检索。
        with graph_lock:
            client = MilvusClient(uri=MILVUS_URI)
            if not client.has_collection(collection_name=COLLECTION_NAME):
                raise HTTPException(
                    status_code=503,
                    detail="知识库集合不存在，请先完成全量入库",
                )

            client.load_collection(collection_name=COLLECTION_NAME)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = DATA_DIR / filename

            # 简单版本不允许上传覆盖已有的不同内容。
            # 已有文件更新仍通过命令行增量入口执行。
            normalized_content = text.encode("utf-8")
            if path.exists():
                if not path.is_file() or path.is_symlink():
                    raise HTTPException(status_code=409, detail="文件名不可用")
                if path.read_bytes() != normalized_content:
                    raise HTTPException(
                        status_code=409,
                        detail="同名文件内容不同，请改名后上传",
                    )
            else:
                path.write_bytes(normalized_content)

            parser = MarkdownParser()
            mv = MilvusVectorSave()
            mv.create_connection()

            result = import_one_file(path, parser, client, mv)

        return {
            **result,
            "message": (
                "内容未变化，已跳过"
                if result["status"] == "skipped"
                else "入库完成"
            ),
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="入库失败，文件已保留，可再次上传重试",
        ) from None
    finally:
        if client is not None:
            client.close()
