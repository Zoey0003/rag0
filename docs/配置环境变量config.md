# 下载后配置与恢复

本文对应当前项目代码。GitHub 保存源码、依赖清单、迁移脚本和 Markdown 知识库资料，不保存真实密钥、本地模型和数据库运行状态。下载旧标签只能恢复该版代码，不能自动恢复当时的聊天记录、记忆或知识库数据库。

## 未上传文件清单

| 文件或目录 | 用途 | 下载后如何准备 |
| --- | --- | --- |
| `backend/.env` | 模型密钥、搜索密钥、记忆数据库连接配置 | 复制 `backend/.env.example` 为 `.env`，填写自己的配置；或从私人备份恢复 |
| `infra/postgres/.env`（本地创建） | Docker PostgreSQL 和 pgAdmin 初始化配置 | 复制同目录 `.env.example` 为 `.env`，填写密码；数据库名称、用户和密码与后端一致 |
| `models/` | 本地 BGE 向量模型 | 重新获取完整 `bge-small-zh-v1.5` 模型，或从本机复制；目标目录 `models/bge-small-zh-v1.5/` |
| `backend/datas/import_manifest.sqlite3` | 记录每个资料文件的哈希、导入状态和块数，供增量导入使用 | 新库由导入代码自动创建；已有完整 Milvus 数据且缺少清单时，核对后运行基线初始化脚本；延续旧数据时与 Milvus 配套备份 |
| `memory_exports/` | 导出的会话 Markdown 文件 | 可重新导出，或从私人备份恢复；不是数据库备份 |
| `.vscode/`、`backend/.idea/` | 编辑器配置 | 可选，不影响应用运行 |
| 各级 `__pycache__/`、`*.pyc` | Python 编译缓存 | 自动生成，不需要恢复 |
| `backend/.test-tmp/`、`.pytest_cache/` | 测试临时文件和缓存 | 自动生成，不需要恢复 |
| `backend/graph2_validation.log`、`backend/regression_validation.log` 等 `*.log` | 运行与验证日志 | 不影响启动；如需审计历史则单独备份 |
| `.venv/`、`venv/`、`node_modules/`、`dist/`（如有） | 本地依赖环境或构建产物 | 根据依赖清单重新安装或构建 |

`.env.*` 默认也被忽略，但 `.env.example` 会上传。模板只能包含变量名、示例和空密钥。

## 后端环境变量

后端固定读取 `backend/.env`，无需把它放在项目根目录。`utils/env_utils.py` 使用 `override=True`，因此该文件会覆盖进程中同名变量；记忆数据库和评测配置使用 `override=False`，加载顺序会影响最终值。建议本地运行统一在该文件中设置。

| 变量 | 作用 | 是否需要 / 默认值 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | 百炼模型鉴权，用于当前 `qwen-plus` 和在线 `text-embedding-v4` | 当前模型配置需要，填自己的密钥 |
| `DASHSCOPE_BASE_URL` | 百炼 OpenAI 兼容接口地址 | 当前模型配置需要；模板提供地址，按账号实际服务区域确认 |
| `TAVILY_API_KEY` | Tavily 联网搜索工具鉴权，由工具库读取 | 当前代码创建搜索工具，需要配置 |
| `MEMORY_DB_HOST` | PostgreSQL 主机地址 | 默认 `127.0.0.1` |
| `MEMORY_DB_PORT` | PostgreSQL 端口 | 默认 `5432`；当前 Compose 主机端口固定为 `5432` |
| `MEMORY_DB_NAME` | 保存用户、会话、消息和记忆的数据库名 | 默认 `rag_memory` |
| `MEMORY_DB_USER` | PostgreSQL 登录用户 | 默认 `rag_user` |
| `MEMORY_DB_PASSWORD` | PostgreSQL 登录密码 | 记忆模块必需，无默认值；与数据库实际密码一致 |
| `OPENAI_API_KEY`、`DEEPSEEK_API_KEY` | `env_utils.py` 读取的预留配置 | 当前启用的模型不使用，无需填写 |

## Docker 数据库变量

`infra/postgres/.env` 供 Docker Compose 读取，后端不会自动读取它。

| 变量 | 作用 |
| --- | --- |
| `MEMORY_DB_NAME`、`MEMORY_DB_USER`、`MEMORY_DB_PASSWORD` | 映射到 PostgreSQL 容器的 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`，用于首次初始化数据库 |
| `MEMORY_DB_HOST`、`MEMORY_DB_PORT` | 模板中用于与后端配置对照；Compose 不使用这两个变量修改主机或端口 |
| `PGADMIN_DEFAULT_EMAIL` | pgAdmin 管理界面初始登录邮箱 |
| `PGADMIN_DEFAULT_PASSWORD` | pgAdmin 管理界面初始登录密码，与数据库密码是两件事 |

已有 PostgreSQL 数据卷时，修改 `.env` 不会自动修改库内原有用户密码。不要为改密码而删除数据卷。

## 可选评测变量

普通问答无需配置下列变量；它们只作用于 `backend/rag_eval/`，不会修改主应用配置。

| 变量 | 作用 / 默认行为 |
| --- | --- |
| `EVAL_MILVUS_URI` | 评测 Milvus 地址，默认 `http://127.0.0.1:19530` |
| `EVAL_COLLECTION` | 评测集合，默认 `t_collection01` |
| `EVAL_BGE_PATH` | 评测本地模型路径，默认 `D:\1pyproject\rag0\models\bge-small-zh-v1.5` |
| `EVAL_GEN_MODEL` | 评测生成模型，默认 `qwen-plus` |
| `EVAL_JUDGE_MODEL` | 裁判模型名，使用裁判时必须显式设置 |
| `EVAL_JUDGE_API_KEY` | 裁判专用密钥，未设置时使用 `DASHSCOPE_API_KEY` |
| `EVAL_JUDGE_BASE_URL` | 裁判接口地址，未设置时使用 `DASHSCOPE_BASE_URL` |

## 换目录需要修改的代码配置

当前主应用以下配置不是环境变量。在 `.env` 写同名变量不会生效。

| 配置 | 所在文件 |
| --- | --- |
| Milvus 地址 `MILVUS_URI`、集合名 `COLLECTION_NAME` | `backend/utils/env_utils.py` |
| 本地模型绝对路径 `model_name` | `backend/llm_models/embeddings_model.py` |
| 知识库绝对路径 `md_dir` | `backend/documents/write_milvus.py` |
| 增量导入和基线初始化的知识库路径 `DATA_DIR` | `backend/documents/incremental_import.py`、`backend/documents/init_import_manifest.py` |
| 页面访问后端的地址 `API_URL` | `frontend/app.py` |

下载到新目录时，按新位置修改模型和资料路径。其他检查脚本也可能含旧绝对路径，可在 IDE 全局搜索 `D:\1pyproject\rag0`。Milvus 记录的 `source` 使用绝对文件路径，移动资料后，旧数据和清单不能直接当成新路径下的导入状态使用。

## 首次在新电脑运行

以下假设下载位置为 `D:\1pyproject\rag0`，且已安装 Conda 和 Docker Desktop。已有环境可跳过创建步骤。

```powershell
cd D:\1pyproject\rag0
conda create -n rag0 python=3.11
conda activate rag0
python -m pip install -r backend/requirements-lock.txt

Copy-Item backend/.env.example backend/.env
Copy-Item infra/postgres/.env.example infra/postgres/.env
```

编辑两个 `.env`，填写密钥和密码；复制命令仅在目标文件不存在时执行，避免覆盖已有配置。依赖锁定清单尚未在全新环境完整验证，安装失败时按实际错误处理。

准备完整模型目录，检查上一节的绝对路径。然后启动 Docker Desktop，再启动记忆数据库：

```powershell
cd D:\1pyproject\rag0\infra\postgres
docker compose up -d
docker compose ps

cd D:\1pyproject\rag0\backend
python -X utf8 -m memory.database
python -m alembic upgrade head
```

项目 README 使用的 Milvus Compose 文件位于 `D:\milvus\compose-local.yml`，它不在本仓库中。新电脑需要另行准备 Milvus 部署文件及服务；原电脑应单独备份这个文件及其依赖配置。若仍使用该位置：

```powershell
docker compose -f D:\milvus\compose-local.yml up -d
Test-NetConnection 127.0.0.1 -Port 19530
```

新 Milvus 没有知识库数据时，需要导入仓库的 `md/` 资料。在 `backend/` 执行：

```powershell
python -X utf8 -m documents.write_milvus
python -X utf8 -m scripts.check_full_import
python -X utf8 -m documents.init_import_manifest
```

**`write_milvus` 会删除并重建目标集合。仅在新库或明确要重建时运行；已有数据要保留时跳过。** 基线初始化目前要求 430 个文件、2177 个正文块，并且清单为空；资料或分块方式改变后不能照搬这些预期值。

最后分别打开两个终端，激活 `rag0` 环境：

```powershell
# 终端一
cd D:\1pyproject\rag0\backend
python -X utf8 -m uvicorn api:app --host 127.0.0.1 --port 8000
```

```powershell
# 终端二
cd D:\1pyproject\rag0\frontend
python -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

浏览器访问 `http://127.0.0.1:8501`。

## 保留原有运行数据

单独备份以下内容到私人存储，不提交真实密钥或个人会话到仓库：

- 两个 `.env`、完整模型目录及外部 Milvus Compose 配置。
- PostgreSQL 数据库备份：保存用户、会话、消息、摘要和长期记忆。`memory_exports/` 不能代替它。
- Milvus 的完整部署数据备份：需要按部署方式备份所有相关存储，不能只保存 Compose 文件。
- 与 Milvus 同一时点的导入清单 SQLite 文件；备份前停止导入，避免记录与向量数据不同步。
- 需要保留的会话导出文件。

恢复旧代码时，应确认数据库迁移版本与旧代码兼容；仅下载旧标签不会回退数据库结构。需要完整恢复某一时点时，使用同一时点的代码和数据库备份。
