# RAG_PROJECT 文件说明

本文档说明 `RAG_PROJECT` 中各目录和文件的职责，以及主要的文档入库和问答流程。

## 1. 项目定位

这是一个基于 LangChain、LangGraph 和 Milvus 的中文技术知识库 RAG 项目，当前围绕半导体、芯片制造和光刻技术等内容提供：

- Markdown 文档解析、标题合并和语义切片。
- 使用 BGE 中文 embedding 和 Milvus 的 dense + sparse 混合检索。
- 基于工具调用的 Agent RAG 流程。
- 基于 LangGraph 的检索、评分、查询改写、网络搜索和答案校验流程。
- 基于 Tavily 的外部网络搜索兜底。

## 2. 目录总览

项目根目录为 `D:\1pyproject\rag0`。业务代码放在 `backend/`，项目文档放在 `docs/`，数据库部署配置放在 `infra/`。

```text
rag0/
├── README.md                         # 项目介绍与启动入口
├── .gitignore                        # Git 忽略规则
│
├── docs/                             # 项目文档
│   ├── PROJECT_STRUCTURE.md          # 目录与模块说明
│   ├── quickstart.md                 # 快速启动指南
│   ├── process.md                    # 开发进度与待办
│   ├── memory.md                     # 记忆机制与存储设计
│   ├── light.md                      # 技术亮点
│   ├── help.md                       # 常用命令与操作说明
│   ├── references/                   # 参考 PDF
│   └── images/                       # 文档配图
│
├── infra/                            # 基础设施部署配置
│   └── postgres/
│       ├── compose.yml               # PostgreSQL Docker Compose 配置
│       └── .env.example              # 数据库环境变量示例
│
├── models/                           # 本地模型文件
│   └── bge-small-zh-v1.5/             # BGE 中文向量模型
├── md/                               # 本地知识库 Markdown 文档
├── memory_exports/                   # 记忆导出目录，不是数据库存储目录
│
└── backend/                          # Python 源码与运行配置
    ├── .env                          # 本地环境变量与密钥，不提交 Git
    ├── api.py                        # FastAPI 接口
    ├── app.py                        # Streamlit 聊天界面
    ├── main.py                       # 命令行入口
    ├── requirements-lock.txt         # Python 依赖版本清单
    ├── alembic.ini                   # 数据库迁移配置
    │
    ├── migrations/                   # 数据库结构迁移
    │   ├── env.py                    # 迁移连接与模型元数据配置
    │   ├── script.py.mako            # 迁移脚本模板
    │   └── versions/                 # 按版本保存的迁移脚本
    │
    ├── memory/                       # 会话与记忆模块，持续开发中
    │   ├── __init__.py
    │   ├── database.py               # PostgreSQL 连接与事务会话
    │   └── models.py                 # 用户、会话、消息数据模型
    │
    ├── documents/                    # 文档解析与入库
    │   ├── markdown_parser.py        # Markdown 解析与分块
    │   ├── milvus_db.py              # Milvus 操作封装
    │   ├── write_milvus.py           # 全量入库
    │   ├── import_manifest.py        # 文件指纹与入库清单
    │   ├── init_import_manifest.py   # 初始化已有文档清单
    │   └── incremental_import.py     # 增量入库
    │
    ├── tools/
    │   └── retriever_tools.py        # 本地混合检索封装
    │
    ├── llm_models/
    │   ├── all_llm.py                # 大模型与联网搜索工具配置
    │   └── embeddings_model.py       # 向量模型配置
    │
    ├── graph2/                       # 当前主要 RAG 工作流
    │   ├── graph_2.py                # 节点连接与条件路由
    │   ├── graph_state2.py           # 工作流状态
    │   ├── query_route_chain.py      # 本地与联网检索路由
    │   ├── retriever_node.py         # 本地检索节点
    │   ├── grade_documents_node.py   # 文档相关性筛选
    │   ├── grader_chain.py           # 文档相关性判断链
    │   ├── transform_query_node.py   # 问题改写节点
    │   ├── web_search_node.py        # 联网搜索节点
    │   ├── generate_node2.py         # 答案生成节点
    │   ├── grade_hallucinations_chain.py  # 答案依据检查
    │   └── grade_answer_chain.py     # 回答有效性检查
    │
    ├── graph/                        # 早期工作流实现
    ├── agent/                        # Agent 实现
    ├── utils/                        # 环境配置、日志等公共工具
    │
    ├── scripts/                      # 手动检查与维护脚本
    │   ├── __init__.py
    │   ├── check_full_import.py      # 全量入库核对
    │   ├── check_graph2.py           # 问答流程检查
    │   └── draw_png.py               # 工作流图生成
    │
    ├── tests/                        # 测试与调试脚本
    │   ├── __init__.py
    │   └── test_*.py
    │
    ├── rag_eval/                     # RAG 对比评测模块
    │   ├── README.md
    │   ├── config.py                 # 实验配置
    │   ├── common.py                 # 公共函数与指标计算
    │   ├── retrieval.py              # 对比检索方法
    │   ├── run.py                    # 实验运行入口
    │   ├── evaluate_ragas.py         # Ragas 生成质量评估
    │   ├── test_metrics.py           # 评测指标单元测试
    │   ├── requirements-ragas.txt    # 评测依赖
    │   ├── data/                     # 问题集与标注数据
    │   └── results/                  # 实验结果，运行后生成
    │
    └── datas/                        # 本地辅助数据
        ├── import_manifest.sqlite3   # 增量入库清单数据库
        ├── md/                       # 示例文档
        ├── batch_test_md/            # 小批量测试文档
        ├── batch_test_20_md/          # 20 文件测试文档
        └── output/                   # 解析输出
```

各 Python 包通常包含 `__init__.py`，上图省略了部分文件。

运行后端、迁移及检查脚本时，先进入源码目录：

```powershell
cd D:\1pyproject\rag0\backend
```

PostgreSQL 会话数据保存在 Docker 数据卷中；Milvus 知识库数据由其原有部署管理，当前配置文件位于 `D:\milvus\docker-compose.yml`。

## 3. 文档数据和产物

### `datas/`

- `datas/md/`：待解析的 Markdown 知识库文件。项目中的示例内容包括 FAQ、技术报告、产品说明和故障排查文档。
- `datas/layout-parser-paper.pdf`：开源的 Python 工具包 LayoutParser的论文。
- `datas/output/`：文档处理或解析产生的 JSON 结果文件。它们属于数据产物，不是运行逻辑。

## 4. 文档处理和 Milvus 入库

### `documents/markdown_parser.py`

定义 `MarkdownParser`，负责把 Markdown 文件转换为 LangChain `Document`：

1. 使用 `UnstructuredMarkdownLoader` 按元素解析 Markdown。
2. 清理部分 metadata，并根据标题层级合并内容。
3. 对超过 5000 字符的内容使用 `SemanticChunker` 做语义切分。
4. 返回带有标题、类别等 metadata 的文档列表。

直接运行该文件时，会解析一个硬编码的示例 Markdown 文件并打印文档内容和 metadata。

### `documents/milvus_db.py`

定义 `MilvusVectorSave`，负责 Milvus collection 和文档写入：

- `create_collection()`：创建 schema、BM25 sparse 字段、512 维 dense 字段及对应索引。
- `create_connection()`：创建 LangChain `Milvus` vector store，绑定 BGE embedding 和 BM25 内置函数。
- `add_documents()`：把 `Document` 列表写入 Milvus。

文件底部的脚本入口会解析单个 Markdown 文件、删除并重建 collection、写入文档，然后打印 collection、索引和过滤查询结果。注意：重建 collection 会删除现有 collection 中的数据。

### `documents/write_milvus.py`

提供面向大量 Markdown 文件的多进程入库流程：

- `file_parser_process()`：扫描目录、解析 Markdown，并以批次形式写入进程队列。
- `milvus_writer_process()`：从队列读取批次并写入 Milvus。
- `__main__`：创建 collection，启动解析进程和写入进程并等待结束。

该文件适合批量导入；其中的示例目录是硬编码路径，实际运行前需要修改。

## 5. 模型和外部服务

### `utils/env_utils.py`

负责环境配置：

- 通过 `python-dotenv` 加载环境变量。
- 读取 `OPENAI_API_KEY` 和 `DEEPSEEK_API_KEY`。
- 定义 Milvus 地址 `MILVUS_URI` 和 collection 名称 `COLLECTION_NAME`。

Milvus 地址当前直接写在代码中，生产环境建议改为环境变量，并避免在代码中保存服务地址和密钥配置。

### `llm_models/all_llm.py`

创建全局聊天模型 `llm`，当前使用 OpenAI 兼容接口和 `gpt-4o-mini`。同时创建 Tavily `web_search_tool`，供 `graph2` 的网络搜索节点使用。文件中保留了 DeepSeek 配置示例，但当前没有启用。

### `llm_models/embeddings_model.py`

定义两种 embedding：

- `openai_embedding`：OpenAI 兼容 embedding，主要用于语义切片。
- `bge_embedding`：本地 `BAAI/bge-small-zh-v1.5`，CPU 推理并归一化向量，主要用于 Milvus dense 检索。

## 6. 检索工具

### `tools/retriever_tools.py`

初始化 Milvus 连接并创建全局 `retriever` 和 `retriever_tool`：

- 默认返回最多 4 个结果。
- 使用相似度检索，并配置 `rrf` 排序。
- 过滤 metadata 中 `category == "content"` 的文档。
- 通过 `create_retriever_tool()` 将检索器暴露给 Agent 和 LangGraph 工具节点。

该模块在导入时就会连接 Milvus，因此没有 Milvus 服务或配置时，导入依赖它的模块也可能失败。

## 7. 第一套流程：`graph/`

这是一套以消息列表为状态、支持工具调用和会话记忆的 Agent RAG 流程。

### `graph/graph_state1.py`

- 定义 `AgentState`，其中 `messages` 使用 LangGraph 的 `add_messages` 累积消息。
- 定义 `Grade`，用于表示文档相关性评分的 `yes`/`no` 结果。

### `graph/agent_node.py`

让 LLM 绑定 `retriever_tool`，根据当前用户消息决定直接回答还是调用检索工具。

### `graph/rewrite_node.py`

当检索文档不相关时，调用 LLM 改写用户问题，然后把改写结果追加回消息状态。

### `graph/generate_node.py`

读取用户问题和检索工具返回的文档，使用提示词和 LLM 生成最终答案，并追加 `AIMessage`。

### `graph/get_human_message.py`

从消息列表中获取最近一条人类消息，供评分、改写和生成节点使用。

### `graph/graph1.py`

组装并执行第一套图：

```text
START -> agent
          ├─ 直接结束
          └─ 调用 retriever -> grade_documents
                                  ├─ 文档相关 -> generate -> END
                                  └─ 文档不相关 -> rewrite -> agent
```

它使用 `MemorySaver` 和 `thread_id` 保存会话状态，并在文件底部启动交互式命令行循环。

### `graph/graph_rag1-2.png`

第一套图的可视化结果，不参与运行逻辑。

## 8. 第二套流程：`graph2/`

这是一套显式维护 `question`、`documents`、`generation` 和 `transform_count` 的路由式 RAG 流程。

### `graph2/graph_state2.py`

定义 `GraphState`：

- `question`：当前问题。
- `documents`：检索或网络搜索得到的文档。
- `generation`：模型生成的答案。
- `transform_count`：问题改写次数。

### 路由和检索节点

- `graph2/query_route_chain.py`：使用结构化输出，把问题路由到 `vectorstore` 或 `web_search`。
- `graph2/retriever_node.py`：调用全局 Milvus retriever，写入 `documents`。
- `graph2/web_search_node.py`：调用 Tavily，合并搜索内容并包装成 `Document`。
- `graph2/transform_query_node.py`：调用 LLM 优化问题，并递增 `transform_count`。

### 评分链和评分节点

- `graph2/grader_chain.py`：定义 `GradeDocuments` 和检索文档相关性评分链。
- `graph2/grade_documents_node.py`：逐个文档评分，只保留评分为 `yes` 的文档。
- `graph2/grade_hallucinations_chain.py`：检查生成内容是否得到参考文档支持。
- `graph2/grade_answer_chain.py`：检查生成内容是否真正回答了用户问题。

### `graph2/generate_node2.py`

把多个检索文档或单个网络搜索文档格式化为上下文，调用 LLM 生成 `generation`。

### `graph2/graph_2.py`

组装并执行第二套图：

```text
START -> route_question
          ├─ web_search -> generate
          └─ retrieve -> grade_documents
                            ├─ 有相关文档 -> generate
                            ├─ 无相关文档且未超过次数 -> transform_query -> retrieve
                            └─ 改写次数达到上限 -> web_search

generate -> 检查幻觉和答案质量
             ├─ useful -> END
             ├─ not useful -> transform_query
             └─ not supported -> generate
```

文件底部是交互式命令行入口，使用 `graph.stream()` 打印节点执行过程和最终答案。

## 9. Agent 入口

### `agent/rag_agent.py`

创建一个基于 `create_tool_calling_agent()` 的 LangChain Agent：

- 使用 `retriever_tool` 作为知识库工具。
- 使用 `AgentExecutor` 执行工具调用。
- 使用 `RunnableWithMessageHistory` 按 `session_id` 保存内存中的聊天历史。

当前文件导入后会立即执行一条示例问题并打印结果，不只是定义模块；作为库导入或测试时需要注意这个副作用。

## 10. 工具和辅助文件

### `draw_png.py`

调用 LangGraph 的 Mermaid PNG 导出能力，把图结构保存为图片；绘图失败时记录异常，不影响核心流程定义。

### `utils/log_utils.py`

提供项目统一 logger，供文档解析、图节点和入库进程输出阶段日志。

### `utils/print_utils.py`

定义 `_print_event()`，用于打印第一套图的消息事件，避免重复打印同一个消息，并截断过长内容。

### 各目录的 `__init__.py`

把 `agent`、`documents`、`graph`、`graph2`、`llm_models` 和 `tools` 声明为 Python 包；目前主要承担包初始化作用。

## 11. 入口和建议运行顺序

### 批量建立知识库

1. 确认 Milvus 服务可访问，配置模型所需的 API key。
2. 修改 `documents/write_milvus.py` 中的 Markdown 目录。
3. 运行 `write_milvus.py`，完成 collection 创建和批量写入。

### 运行问答流程

- 第一套 Agent 流程：运行 `graph/graph1.py`。
- 第二套路由式流程：运行 `graph2/graph_2.py`。
- 简单 AgentExecutor 示例：运行 `agent/rag_agent.py`。

运行前需要确认当前工作目录和 Python import 路径能让 `documents`、`graph2`、`llm_models` 等顶层包被找到。

## 12. 非业务文件

- `.idea/`：PyCharm 项目配置，不属于运行核心。
- `__pycache__/`：Python 字节码缓存，可以删除并不影响源码。
- `graph_rag1.png`、`graph_rag1-2.png`、`graph_rag2.png`：LangGraph 可视化图片。
- `datas/output/*.json`：处理结果或中间数据，不是 Python 模块。
- `main.py`：当前仍是 IDE 创建的 `print_hi()` 示例，没有接入 RAG 流程。