from logging.config import fileConfig

from alembic import context
config = context.config

import sys
from pathlib import Path
# 获取 backend 的绝对路径
backend_dir = Path(__file__).resolve().parent.parent / "backend"
# 添加到模块搜索路径
sys.path.insert(0, str(backend_dir))
from memory.database import Base, engine
import memory.models  # 注册模型，使 Base.metadata 包含所有模型表


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """生成 SQL 文件，不连接数据库。"""
    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """连接 PostgreSQL，执行迁移或比较模型与实际表结构。"""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

if __name__ == "__main__":
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()