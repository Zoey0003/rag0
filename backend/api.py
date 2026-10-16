"""旧启动入口，兼容 uvicorn api:app。"""

from app.main import app

__all__ = ["app"]