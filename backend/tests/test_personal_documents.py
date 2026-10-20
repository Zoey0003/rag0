"""离线验证个人文档权限、发布和删除；不调用真实模型/Milvus。"""
import json
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.auth.models import User
from app.modules.documents import repository, service
from app.modules.documents.models import KnowledgeDocument


class FakeVectors:
    def __init__(self):
        self.rows = {}
        self.fail_write = False
        self.fail_delete = False

    def add_documents(self, docs):
        for doc in docs:
            source = doc.metadata["source"]
            self.rows[source] = self.rows.get(source, 0) + 1
            if self.fail_write:
                raise RuntimeError("partial write")

    def sources(self, expression):
        return json.loads(expression.split("source in ", 1)[1])

    def query(self, **kwargs):
        return [{"count(*)": sum(self.rows.get(s, 0) for s in self.sources(kwargs["filter"]))}]

    def delete(self, **kwargs):
        if self.fail_delete:
            raise RuntimeError("delete unavailable")
        for source in self.sources(kwargs["filter"]):
            self.rows.pop(source, None)


class FakeParser:
    def parse_markdown_to_documents(self, source):
        return [SimpleNamespace(page_content=Path(source).read_text(encoding="utf-8"),
                                metadata={"source": source, "category": "content"})]


class PersonalDocumentsTest(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[2] / ".test-tmp"
        temp_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_root)
        self.root = patch.dict("os.environ", {"KNOWLEDGE_DATA_DIR": self.tmp.name})
        self.root.start()
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine, tables=[User.__table__, KnowledgeDocument.__table__])
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.a, self.b = uuid4(), uuid4()
        with self.sessions.begin() as db:
            db.add_all([User(id=user_id, name="test", password_hash="test") for user_id in (self.a, self.b)])
        # SQLite 不支持 PostgreSQL advisory lock；该测试不声称验证多进程竞争。
        self.lock = patch.object(repository, "lock_owner")
        self.lock.start()
        self.vectors = FakeVectors()
        self.parser = FakeParser()

    def tearDown(self):
        self.lock.stop()
        self.root.stop()
        self.engine.dispose()
        self.tmp.cleanup()

    def upload(self, user, content=b"# title\ntext", document_id=None):
        return service.upload(self.sessions, user, "same.md", content, self.parser,
                              self.vectors, self.vectors, "test", document_id)

    def expression(self, user):
        with self.sessions() as db:
            return repository.retrieval_expression(db, user)

    def test_same_name_users_are_isolated_and_unknown_shared_sources_excluded(self):
        a, b = self.upload(self.a), self.upload(self.b)
        self.assertNotEqual(a["document_id"], b["document_id"])
        self.vectors.rows["legacy-shared.md"] = 10
        sources_a = self.vectors.sources(self.expression(self.a))
        sources_b = self.vectors.sources(self.expression(self.b))
        self.assertTrue(set(sources_a).isdisjoint(sources_b))
        self.assertNotIn("legacy-shared.md", sources_a)
        with self.sessions() as db:
            self.assertIsNone(repository.get_owned(db, self.b, a["document_id"]))
            self.assertEqual(len(repository.list_documents(db, self.a)), 1)

    def test_unchanged_skip_and_update_publishes_new_source(self):
        first = self.upload(self.a)
        old = self.expression(self.a)
        self.assertEqual(self.upload(self.a)["status"], "skipped")
        self.assertEqual(len(self.vectors.rows), 1)
        updated = self.upload(self.a, b"# new\nupdated")
        self.assertEqual(updated["document_id"], first["document_id"])
        self.assertNotEqual(self.expression(self.a), old)
        self.assertEqual(len(self.vectors.rows), 1)

    def test_partial_write_keeps_old_source_and_retry_succeeds(self):
        self.upload(self.a)
        old = self.expression(self.a)
        self.vectors.fail_write = True
        with self.assertRaises(RuntimeError):
            self.upload(self.a, b"changed")
        self.assertEqual(self.expression(self.a), old)
        self.vectors.fail_write = False
        self.assertEqual(self.upload(self.a, b"changed")["status"], "updated")

    def test_other_user_cannot_update_or_delete(self):
        result = self.upload(self.a)
        for action in (
            lambda: self.upload(self.b, b"attack", result["document_id"]),
            lambda: service.delete(self.sessions, self.b, result["document_id"], self.vectors, "test"),
        ):
            with self.assertRaises(HTTPException) as raised:
                action()
            self.assertEqual(raised.exception.status_code, 404)
        self.assertIsNotNone(self.expression(self.a))

    def test_failed_delete_hidden_and_retry_removes_files_and_manifest(self):
        result = self.upload(self.a)
        self.vectors.fail_delete = True
        with self.assertRaises(RuntimeError):
            service.delete(self.sessions, self.a, result["document_id"], self.vectors, "test")
        self.assertIsNone(self.expression(self.a))
        with self.assertRaises(HTTPException) as raised:
            self.upload(self.a)
        self.assertEqual(raised.exception.status_code, 409)
        self.vectors.fail_delete = False
        service.delete(self.sessions, self.a, result["document_id"], self.vectors, "test")
        self.assertEqual(self.vectors.rows, {})
        self.assertEqual(list(Path(self.tmp.name).rglob("*.md")), [])
        with self.sessions() as db:
            self.assertEqual(repository.list_documents(db, self.a), [])

    def test_input_validation_and_bom_normalization(self):
        for name, content, status in [
            ("../x.md", b"text", 400), ("x.md", b"", 400),
            ("x.md", b"\xff", 400), ("x.md", b" " * (5 * 1024 * 1024 + 1), 413),
        ]:
            with self.assertRaises(HTTPException) as raised:
                service.decode_upload(name, content)
            self.assertEqual(raised.exception.status_code, status)
        self.assertEqual(service.decode_upload("x.md", b"\xef\xbb\xbftext"), b"text")

    def test_api_auth_and_foreign_document_rejected_before_vector_access(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        with patch.dict(sys.modules, {"app.db.session": SimpleNamespace(SessionLocal=self.sessions)}):
            router = importlib.import_module("app.modules.documents.router")
        app = FastAPI()
        app.include_router(router.router)
        first = self.upload(self.a)
        with patch.object(router, "SessionLocal", self.sessions), patch.object(router, "vector_resources") as vectors:
            with TestClient(app) as client:
                self.assertEqual(client.get("/documents").status_code, 401)
                app.dependency_overrides[router.require_user_id] = lambda: self.b
                self.assertEqual(client.get("/documents").json(), [])
                path = f"/documents/{first['document_id']}"
                self.assertEqual(client.delete(path).status_code, 404)
                self.assertEqual(client.put(path + "/content", files={"file": ("x.md", b"attack")}).status_code, 404)
                vectors.assert_not_called()

    def test_retrieval_passes_owner_filter_to_search_without_global_mutation(self):
        from unittest.mock import Mock

        self.upload(self.a)
        self.upload(self.b)
        store = Mock()
        store.similarity_search.return_value = ["owned result"]
        with patch.dict(sys.modules, {
            "app.db.session": SimpleNamespace(SessionLocal=self.sessions),
            "tools.retriever_tools": SimpleNamespace(mv=SimpleNamespace(vector_store_saved=store)),
        }):
            node = importlib.import_module("graph2.retriever_node")
            with patch.object(node, "SessionLocal", self.sessions):
                self.assertEqual(node.retrieve({"question": "test"})["documents"], [])
                store.similarity_search.assert_not_called()
                result = node.retrieve({"question": "test", "user_id": str(self.a)})
                self.assertEqual(result["documents"], ["owned result"])
                self.assertEqual(store.similarity_search.call_args.kwargs["expr"], self.expression(self.a))
                self.assertNotEqual(store.similarity_search.call_args.kwargs["expr"], self.expression(self.b))


if __name__ == "__main__":
    unittest.main()
