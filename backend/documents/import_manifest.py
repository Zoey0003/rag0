import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "datas" / "import_manifest.sqlite3"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    #Python 和这个 SQLite 数据库文件之间的一条连接
    conn = sqlite3.connect(DB_PATH)#SQLite 数据库连接对象
    conn.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            source TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            chunk_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)#创建imports 表
    #execute表示用这个 SQLite 连接对象执行一条 SQL 语句。
    return conn


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_record(source: str):
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM imports WHERE source = ?",
            (source,),
        ).fetchone()
        return dict(row) if row else None


def save_record(source, content_hash, chunk_count, status, error=None):
    with connect() as conn:
        conn.execute("""
            INSERT INTO imports
                (source, content_hash, chunk_count, status, error)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                content_hash = excluded.content_hash,
                chunk_count = excluded.chunk_count,
                status = excluded.status,
                error = excluded.error,
                updated_at = CURRENT_TIMESTAMP
        """, (source, content_hash, chunk_count, status, error))