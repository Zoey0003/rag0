# Redis 限流、Celery 后台任务与个人知识库隔离代码说明

整理日期：2026-10-20。对比基线：`221581b`（按业务模块分层整理后端目录并保留兼容入口）。

本文说明当前工作区中这三个功能的新增文件、修改位置、关键代码和调用流程。代码片段为关键节选，省略的上下文请查看文件链接；本文不表示相关服务、迁移和测试已在实际环境验证通过。

## 一、Redis 限流

### 1. 改了哪些文件

| 文件 | 变更 | 作用 |
|---|---|---|
| [redis_client.py](../backend/app/core/redis_client.py) | 新增 | 创建 Redis 客户端、复用连接池、统一键名前缀 |
| [rate_limit.py](../backend/app/core/rate_limit.py) | 新增 | 计数窗口限流、令牌桶限流和认证限流依赖 |
| [auth/router.py](../backend/app/modules/auth/router.py) | 修改 | 注册和登录接入按 IP 限流 |
| [chat/router.py](../backend/app/modules/chat/router.py) | 修改 | 问答接入按用户令牌桶限流 |
| [check_rate_limit.py](../backend/app/core/check_rate_limit.py) | 新增 | 手动检查超限和不同身份计数隔离 |
| [check_token_bucket.py](../backend/app/core/check_token_bucket.py) | 新增 | 手动检查令牌消耗和等待后的补充 |
| [compose.yml](../infra/compose/compose.yml) | 新增部署文件 | 在 PostgreSQL、pgAdmin 之外增加 Redis |

### 2. Redis 连接：redis_client.py

核心函数：

```python
def redis_key(name: str) -> str:
    prefix = os.getenv("REDIS_PREFIX", "rag0")
    return f"{prefix}:{name}"

@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )
```

`redis_key()` 避免与其他项目的键混淆；`get_redis()` 在每个进程内复用客户端和连接池。不同 API worker 连接同一个 Redis，因此能共享限流状态。

### 3. 计数窗口限流：rate_limit.py

`check_rate_limit(scope, identity, limit, window_seconds)` 对身份做 SHA-256 哈希，生成计数键，再执行 Lua：

```lua
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
```

计数和首次设置过期时间在 Redis 内原子执行。窗口从键第一次创建开始计时，不是按自然分钟对齐，也不是滑动窗口。

超过次数返回 `429` 和 `Retry-After`；Redis 操作异常返回 `503`。

### 4. 注册、登录的接入位置：auth/router.py

新增依赖：

```python
from app.core.rate_limit import auth_rate_limit

@router.post("/register", status_code=201,
             dependencies=[Depends(auth_rate_limit)])
def register(request: RegisterRequest):
    ...

@router.post("/login", dependencies=[Depends(auth_rate_limit)])
def login(request: LoginRequest):
    ...
```

`auth_rate_limit()` 的参数：

```python
ip = request.client.host if request.client else "unknown"
check_rate_limit(
    scope="auth", identity=ip,
    limit=10, window_seconds=60,
)
```

注册与登录使用同一个 `auth` scope，因此同一 IP 的两类请求共用限额。例如连续登录 8 次再注册 2 次，下一次认证请求会被拒绝，直到窗口过期。这里读取的是 `request.client.host`。

### 5. 令牌桶限流与问答接入

`check_token_bucket()` 与计数窗口不同：桶内有令牌时允许请求，每个请求消耗一个令牌，令牌随时间补充。

`chat/router.py` 在进入问答锁之前调用：

```python
check_token_bucket(
    scope="ask",
    identity=str(user_id),
    capacity=10,
    refill_seconds=6,
)
```

关键 Lua 逻辑：

```lua
local time = redis.call('TIME')
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000
-- 读取已有 tokens、updated_at；首次访问时初始化满桶
local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * refill_rate)
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
else
    retry_after = math.ceil((1 - tokens) / refill_rate)
end
```

时间取自 Redis，避免多个 API worker 使用不同本地时钟。桶容量为 10，每 6 秒补充一个，允许短时间突发，长期补充速度约为每分钟 10 个。

例如一个用户快速消耗 10 个令牌后，紧接着的请求会返回 `429`；约 6 秒后可再获得一个令牌。不同用户各自计数。令牌消耗发生在后续问题校验、模型调用之前，后续问答失败也不会自动退回令牌。

### 6. 调用流程与配置

```text
注册/登录 → auth_rate_limit → Redis 计数脚本 → 通过或 429
问答 → 身份验证 → check_token_bucket → 通过后获取 graph_lock → 执行问答
```

| 环境变量 | 默认值 | 用途 |
|---|---|---|
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | 限流连接 |
| `REDIS_PREFIX` | `rag0` | 限流键前缀 |

新的 Compose 位于 `infra/compose/`，替代原 `infra/postgres/` 部署文件位置，Redis 使用 `redis:7.4`，端口绑定本机，开启 AOF 和 `everysec` 刷盘，并配置数据卷和健康检查。

## 二、Celery 后台记忆提取任务

### 1. 改了哪些文件

| 文件 | 变更 | 作用 |
|---|---|---|
| [core/celery_app.py](../backend/app/core/celery_app.py) | 新增 | Celery 实例、队列和 Redis 配置 |
| [app/tasks.py](../backend/app/tasks.py) | 新增 | 定义记忆提取任务及重试策略；另有加法示例任务 |
| [memory/task_memory.py](../backend/app/modules/memory/task_memory.py) | 新增 | 数据库待投递任务模型 |
| [memory/task_dispatcher.py](../backend/app/modules/memory/task_dispatcher.py) | 新增 | 向 Celery 投递任务并更新投递状态 |
| [scripts/dispatch_memory_tasks.py](../backend/scripts/dispatch_memory_tasks.py) | 新增 | 定期扫描未投递记录并补投 |
| [chat/router.py](../backend/app/modules/chat/router.py) | 修改 | 替换 BackgroundTasks，保存待办后投递 |
| [conversations/models.py](../backend/app/modules/conversations/models.py) | 修改 | 消息增加提取完成时间 |
| [memory/extractor.py](../backend/app/modules/memory/extractor.py) | 修改 | 重复检查、完成标记和失败重新抛出 |
| [db/models.py](../backend/app/db/models.py) | 修改 | 导出新任务模型供元数据加载 |

本次后台化的是普通成功问答后的长期记忆提取。问答生成、文档入库、会话摘要仍在原同步流程中；“记住：”命令直接同步保存偏好。

### 2. Celery 配置：core/celery_app.py

```python
celery_app = Celery(
    "rag0",
    broker=os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/2"),
    include=["app.tasks"],
)
```

主要配置包括 JSON 序列化、默认队列 `rag0`、结果保留一天、启动时重试连接以及 `worker_prefetch_multiplier=1`。默认 Redis DB 0 用于限流，DB 1 用于任务队列，DB 2 用于结果；这是逻辑分库，仍可属于同一个 Redis 实例。

### 3. 任务入口与重试：app/tasks.py

```python
@celery_app.task(
    name="rag0.extract_memories",
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def extract_memories_task(user_id: str, source_message_id: int) -> None:
    from uuid import UUID
    from app.modules.memory.extractor import extract_and_save_memories

    extract_and_save_memories(
        user_id=UUID(user_id),
        source_message_id=source_message_id,
    )
```

任务只传用户 ID 和来源消息 ID，正文由 worker 从数据库读取。异常最多自动重试 3 次，并有退避和随机抖动；延迟确认与 worker 丢失配置用于降低执行中断后的任务丢失风险，不代表任务绝不会重复。

### 4. 数据库待办：memory/task_memory.py

`MemoryExtractionTask` 对应 `memory_extraction_tasks`：

| 字段 | 意义 |
|---|---|
| `source_message_id` | 主键和消息外键，一条来源消息一条待办 |
| `created_at` | 创建时间 |
| `published_at` | 成功投递时间；NULL 表示尚未记录成功投递 |
| `last_error` | 上一次投递错误 |

数据库待办用于弥补“消息保存成功，但 Redis 暂时无法投递”的情况。

### 5. 问答入口的改动：chat/router.py

旧方式是在响应后台使用 `BackgroundTasks.add_task()`。现在在保存成功问答的事务里增加：

```python
source_message_id = user_message.id
db.add(MemoryExtractionTask(source_message_id=source_message_id))
```

用户消息、助手消息和待办一起提交；离开事务后执行：

```python
try:
    publish_memory_task(source_message_id)
except Exception:
    logger.exception("待办任务投递异常：来源消息=%s", source_message_id)
```

投递异常不会撤销已经保存的回答。API 仍会尝试投递，但不等待 worker 调用模型完成记忆提取。达到回答尝试上限而不保存有效历史的分支，也不会建立这条待办。

### 6. 投递与补投

[task_dispatcher.py](../backend/app/modules/memory/task_dispatcher.py) 的 `publish_memory_task()` 查询尚未投递的待办，并加行锁：

```python
.where(
    MemoryExtractionTask.source_message_id == source_message_id,
    MemoryExtractionTask.published_at.is_(None),
)
.with_for_update(skip_locked=True)
```

随后投递：

```python
extract_memories_task.apply_async(
    kwargs={"user_id": str(user_id), "source_message_id": source_message_id},
    retry=False,
)
```

成功设置 `published_at`，失败保存错误并保留未投递状态。

[dispatch_memory_tasks.py](../backend/scripts/dispatch_memory_tasks.py) 中：

- `dispatch_once()`：最多读取 100 条未投递待办，逐条调用投递函数。
- `main()`：每 10 秒扫描一次，需作为独立程序运行。

### 7. 提取幂等：extractor.py 与消息模型

`ChatMessage` 新增：

```python
memory_extracted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True,
)
```

`extract_and_save_memories()` 在调用模型前检查完成标记，保存时锁定用户和来源消息，再次检查标记，避免重复任务重复写入。

保存候选记忆后，在同一事务中标记：

```python
message.memory_extracted_at = datetime.now(timezone.utc)
```

即便候选列表为空，也会记录已经处理，避免同一消息不断重新提取。异常处理改为记录日志后 `raise`，使 Celery 能触发自动重试；文件里的“失败时仅记录日志”旧 docstring 尚未同步这一行为。

原有候选规则仍保留：一次最多 3 条，置信度至少 0.85，依据必须出现在用户原文。

### 8. 例子、状态和启动

用户说“以后技术问题都用通俗语言解释”：

```text
问答完成 → 消息与待办同事务提交 → 投递 Redis 队列
    → Celery worker → 读取用户原话 → 模型提取偏好
    → 校验与保存 → 标记 memory_extracted_at
```

`published_at` 表示已投递；`memory_extracted_at` 表示消息提取已完成，两者不能互相替代。发送成功而投递状态未提交时仍可能重复发送，因此需要提取端幂等。扫描程序只补投未记录成功投递的任务，不负责自动重跑所有已投递但最终失败的任务。

新增迁移：

- [be088b37f326](../migrations/versions/be088b37f326_add_memory_extraction_completion_.py)：增加提取完成时间。
- [1cf2b2a73698](../migrations/versions/1cf2b2a73698_add_memory_extraction_outbox.py)：增加任务待办表。

在 `backend/` 下分别启动 worker 和扫描程序：

```powershell
python -m celery -A app.core.celery_app:celery_app worker --pool=solo --loglevel=info
python -m scripts.dispatch_memory_tasks
```

## 三、个人知识库管理与检索隔离

### 1. 改了哪些文件

| 文件 | 变更 | 作用 |
|---|---|---|
| [documents/models.py](../backend/app/modules/documents/models.py) | 新增 | 个人文档清单模型 |
| [documents/repository.py](../backend/app/modules/documents/repository.py) | 新增 | 归属查询、写入锁和检索过滤条件 |
| [documents/service.py](../backend/app/modules/documents/service.py) | 新增 | 文件校验、上传更新、删除和来源清理 |
| [documents/router.py](../backend/app/modules/documents/router.py) | 修改 | 文档列表、上传、更新、删除接口 |
| [chat/router.py](../backend/app/modules/chat/router.py) | 修改 | 向图状态传入认证后的用户 ID |
| [graph_state2.py](../backend/graph2/graph_state2.py) | 修改 | 新增 `user_id` 状态字段 |
| [retriever_node.py](../backend/graph2/retriever_node.py) | 修改 | 每次检索传入用户有效来源过滤条件 |
| [db/models.py](../backend/app/db/models.py) | 修改 | 导出文档模型 |
| [frontend/app.py](../frontend/app.py) | 修改 | 上传更新、文档选择和删除确认 |
| [个人文档迁移](../migrations/versions/d20261019a01_personal_documents.py) | 新增 | 创建表、索引、唯一约束 |
| [test_personal_documents.py](../backend/tests/test_personal_documents.py) | 新增 | 隔离、更新与失败重试等测试代码 |
| [.gitignore](../.gitignore) | 修改 | 忽略 `/backend/datas/personal/` |

### 2. 文档模型：models.py

```python
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("owner_id", "filename", name="uq_document_owner_filename"),
    )
```

| 字段 | 作用 |
|---|---|
| `id` | 文档唯一 ID |
| `owner_id` | 所属用户 |
| `filename` | 原始文件名 |
| `content_hash` | 归一化 UTF-8 内容的 SHA-256 |
| `active_source` | 当前有效版本来源路径 |
| `chunk_count` | 当前版本块数 |
| `status` | `ready` 或 `deleting` |
| `updated_at` | 更新时间 |

同一用户同名文件对应同一文档；不同用户可上传同名文件。文件默认按 `backend/datas/personal/<用户ID>/<文档ID>/<版本UUID>.md` 保存，可通过 `KNOWLEDGE_DATA_DIR` 修改根目录。

### 3. 数据查询与互斥：repository.py

| 函数 | 意义 |
|---|---|
| `lock_owner()` | 使用 PostgreSQL 事务级 advisory lock，串行处理同一用户文档写操作 |
| `list_documents()` | 查询当前用户文档列表 |
| `get_owned()` | 同时按用户 ID 和文档 ID 查询，防止越权 |
| `get_named()` | 按用户 ID 和文件名查询，用于同名更新 |
| `retrieval_expression()` | 查询当前用户有效来源，生成 Milvus 过滤表达式 |

归属检查：

```python
KnowledgeDocument.id == UUID(str(document_id)),
KnowledgeDocument.owner_id == owner_id,
```

检索来源查询条件：

```python
KnowledgeDocument.owner_id == owner_id,
KnowledgeDocument.status == "ready",
KnowledgeDocument.active_source.is_not(None),
```

最终返回类似：

```text
category == "content" and source in ["当前用户版本A路径", "当前用户版本B路径"]
```

该方案在共享 Milvus 集合中按已登记来源过滤，没有为每个用户单独创建 collection，也没有修改 Milvus schema。

### 4. 上传与版本更新：service.py

| 函数 | 意义 |
|---|---|
| `data_root()` | 获取个人资料根目录 |
| `document_dir()` | 根据用户 ID、文档 ID 构造目录 |
| `decode_upload()` | 检查文件名、Markdown 后缀、大小、UTF-8 编码和正文 |
| `serialize()` | 返回文档 ID、文件名、状态和块数 |
| `source_filter()` | 构造指定来源的 Milvus 过滤条件 |
| `cleanup_sources()` | 删除来源向量，强一致查询确认无残留，再删除对应文件 |
| `upload()` | 新建或更新文档，校验后发布有效版本 |
| `delete()` | 先隐藏文档，再清理文件、向量和清单 |

仅支持 UTF-8 Markdown，最大 5 MiB；UTF-8 BOM 会归一化。内容相同且已有有效来源时直接跳过：

```python
if record is not None and record.content_hash == digest and record.active_source:
    return serialize(record, "skipped")
```

更新过程：

```text
锁定当前用户写操作 → 查同名或指定 ID 文档 → 创建新版本文件
    → Markdown 解析与分块校验 → 写新向量 → 强一致查询核对块数
    → 更新 active_source 并提交 PostgreSQL → 清理旧版本
```

关键切换代码：

```python
writer.add_documents(docs)
# 核对新来源实际块数等于 len(docs) 后：
old_source = record.active_source
record.active_source = str(candidate)
record.content_hash = digest
record.chunk_count = len(docs)
record.status = "ready"
```

例如“光刻.md”从 3 块更新为 5 块：先写入新版本 5 块，核对后切换有效来源，再清理原 3 块。新版本未发布时仍以旧版本为有效来源。按文档 ID 更新不会隐式修改原文件名。

PostgreSQL 与 Milvus 没有共同事务。失败候选和旧版本清理失败可能留下不可检索的文件或向量，当前没有自动垃圾回收；旧来源清理失败会记录日志，不撤销已经发布的新版本。

### 5. 删除：service.delete()

先在事务中设置并提交：

```python
record.status = "deleting"
```

然后清理该文档目录下的版本文件及对应向量，成功后删除 PostgreSQL 清单。若清理失败，保留 `deleting` 状态，后续检索排除它，用户可重试删除。此状态下的文档也不能直接上传更新。

### 6. 文档接口：router.py

| 接口 | 函数 | 作用 |
|---|---|---|
| `GET /documents` | `list_documents()` | 查询自己的文档和块数 |
| `POST /documents/upload` | `upload_document()` | 上传新文档或同名更新 |
| `PUT /documents/{document_id}/content` | `update_document()` | 更新指定文档正文 |
| `DELETE /documents/{document_id}` | `delete_document()` | 删除指定文档 |

辅助函数：`vector_resources()` 连接并加载集合；`ensure_owned()` 检查归属；`import_upload()` 复用上传更新流程。列表及归属检查不初始化模型，修改操作才连接向量库。

接口通过 `Depends(require_user_id)` 获取身份，客户端不能自行指定文档所有者。上传、更新和删除继续使用进程内 `graph_lock`；同用户跨 API 进程的文档写入互斥由 PostgreSQL advisory lock 提供。这不等于所有问答都具备跨进程全局互斥。

### 7. 问答身份传递与检索隔离

`chat/router.py` 的 `graph.invoke()` 新增：

```python
"user_id": str(user_id),
```

`graph_state2.py` 新增：

```python
user_id: str  # 由认证后的 API 注入
```

`retriever_node.py` 不再直接使用原来的共享检索调用，改为：

```python
owner_id = state.get("user_id")
if not owner_id:
    return {"documents": [], "question": question}
with SessionLocal() as db:
    expression = retrieval_expression(db, UUID(owner_id))
if expression is None:
    return {"documents": [], "question": question}

from tools.retriever_tools import mv
documents = mv.vector_store_saved.similarity_search(
    question, k=4, expr=expression,
    ranker_type="rrf", ranker_params={"k": 100},
)
```

过滤条件每次请求独立传入，不修改全局检索器。`documents/milvus_db.py` 和 `tools/retriever_tools.py` 在这次个人知识库变更中没有修改，复用原向量存储对象和模型能力。

例如 A、B 各上传一份“光刻.md”：两份文档分别登记所属用户和来源路径。A 提问只携带 A 的来源过滤条件，B 的向量即使在同一集合中也不会被该次检索选中。旧共享语料没有个人归属登记，不自动开放；没有身份或没有有效个人来源时返回空本地结果，后续是否联网仍由图流程决定。

### 8. 前端、迁移与测试

`frontend/app.py` 将按钮改为“上传或更新”，侧边栏新增“删除知识资料”：调用 `GET /documents` 获取自己的文档，选择后确认，再调用删除接口；`deleting` 文档会显示“删除未完成，可重试”。目前没有新增独立的知识库管理页面。

迁移 [d20261019a01](../migrations/versions/d20261019a01_personal_documents.py) 创建 `knowledge_documents` 表、用户索引和用户加文件名唯一约束，并接在上述 Celery 待办迁移之后。

新增测试代码包含 8 个测试方法，覆盖：

- 同名文档的用户隔离，以及排除未知共享来源。
- 相同内容跳过、更新发布新来源。
- 新向量部分写入失败时保留旧有效来源，并可重试。
- 其他用户不能更新或删除文档。
- 删除失败后隐藏资料，再次删除完成清理。
- 输入校验和 BOM 归一化。
- API 身份及越权拒绝先于向量资源访问。
- 检索独立传递用户过滤条件，不修改全局检索器。

测试使用模拟向量资源等手段，不能代替真实 Milvus、模型及多进程环境验证。本文整理期间没有重新运行测试或执行数据库迁移。

## 四、三个功能在一次问答中的关系

```text
Bearer 令牌验证 → 得到 user_id
    ↓
Redis 按用户检查令牌桶
    ↓
读取会话摘要、近期历史和长期偏好
    ↓
图状态传入 user_id → 按个人文档有效来源检索 → 生成答案
    ↓
同事务保存问题、答案、记忆提取待办
    ↓
向 Celery 投递任务 → 返回回答
    ↓
独立 worker 提取长期记忆；未投递记录由扫描程序补投
```

使用前需准备 Redis、PostgreSQL、Milvus 和模型依赖，应用新增 Alembic 迁移，并分别运行 API、Celery worker 和待办扫描程序。以上代码说明仅记录当前实现，不将未验证的运行效果视为已完成验证。
