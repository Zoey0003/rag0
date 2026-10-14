# RAG 项目运行说明

当前为 LangGraph + Milvus 命令行问答原型，支持本地知识库检索、文档筛选、答案生成与评分，以及联网搜索回退。

## 当前数据与验证状态

- 集合：`t_collection01`。
- 数据目录：`D:\1pyproject\rag0\md`。
- 用户运行的全量入库及分页核对通过：430 份 Markdown、2177 个正文块，无缺少或额外文件。
- 全量解析字段长度检查通过，最大正文长度为 2531 个 UTF-8 字节。
- 20 文件下两道固定问答已验证；430 文件下完整问答回归尚未取得结果。
- 模型评分通过不保证每个细节正确；换问法测试曾出现“仅适用于”等超出原文的措辞。

详细进度见 [process.md](process.md)。

## 运行环境

现有机器使用 Conda 环境 `rag0`、Docker Desktop 和本地 Milvus。版本清单位于 `backend/requirements-lock.txt`，尚未在全新环境验证安装。

本地 BGE 模型路径为 `D:\1pyproject\rag0\models\bge-small-zh-v1.5`，用于入库及检索向量；百炼在线 Embedding 用于长章节语义切分；`qwen-plus` 用于路由、评分、改写和生成；Tavily 用于联网搜索。

模型调用需配置 `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`，联网搜索需配置 `TAVILY_API_KEY`。项目通过 dotenv 加载环境变量，不要将真实密钥写入文档或提交到代码库。Milvus 当前地址为 `http://127.0.0.1:19530`。

## 启动 Milvus

打开 Docker Desktop，等待引擎启动，再执行：

```powershell
docker compose -f D:\milvus\compose-local.yml up -d --pull never
docker compose -f D:\milvus\compose-local.yml ps -a
Test-NetConnection 127.0.0.1 -Port 19530
```

检查容器健康状态及 `TcpTestSucceeded : True`。

## 启动问答

```powershell
conda activate rag0
cd D:\1pyproject\rag0\backend
python -X utf8 -m graph2.graph_2
```

输入问题开始问答，输入 `q`、`exit` 或 `quit` 退出。本地无相关资料时，流程可能改写问题并最终转联网搜索，因此本地检索失败不一定直接返回资料不足。

## 核对全量数据

在上述环境和源码目录运行：

```powershell
python -X utf8 -m scripts.check_full_import
```

脚本只读分页查询，当前预期结果：

```text
记录数: 2177
文件数: 430
类别: {'content': 2177}
缺少文件: []
额外文件: []
全量入库核对通过
```

未来更换数据集或分块方法时，需要相应调整核对脚本中的预期值。旧 `test_batch_import.py`、`test_batch_import_20.py` 使用历史数据规模，不适用于当前集合。

## 完整问答验证

确认 `check_graph2.py` 的 `questions` 列表包含需要验证的问题，再执行：

```powershell
python -X utf8 -m scripts.check_graph2
```

检查最终答案与保留文档是否一致，是否保留数值、单位及适用条件，是否混用不同工艺资料。脚本断言通过不能替代答案内容核对。

## 重建知识库

确认 `documents/write_milvus.py` 中的数据目录为：

```python
md_dir = r'D:\1pyproject\rag0\md'
```

执行：

```powershell
python -X utf8 -m documents.write_milvus
```

**此操作会删除并重建 `t_collection01`，再写入指定目录的数据。日常问答无需执行入库命令。** 当前没有事务回滚或断点续传，失败时集合可能只包含部分数据。

确认解析与写入子进程均正常结束，再运行 `check_full_import.py` 核对实际数据。长章节语义切分可能调用在线 Embedding。

## 常见问题

- Milvus 无法连接：确认 Docker Desktop 已启动、容器健康及 19530 端口可达，查看日志：

  ```powershell
  docker compose -f D:\milvus\compose-local.yml logs --tail 60
  ```

- `APIConnectionError`：检查网络、代理及模型接口地址；调用鉴权失败时检查对应环境变量。
- 本地模型加载失败：检查 BGE 模型目录是否存在，是否使用 `rag0` 环境运行。
- 输出中文异常：使用文档中的 `python -X utf8` 命令。
- LangGraph 或 Tavily 弃用警告：现有测试中没有阻止运行，后续升级依赖时再验证兼容性。

## 后续事项

全量问答回归、答案来源展示、graph2 多轮对话、增量入库，以及按需求选择 API 或页面功能。

由于改了位置所以上面的部分文件路径需要修改
- [快速启动](docs/quickstart.md)
- [开发进度](docs/process.md)
- [记忆模块设计](docs/memory.md)