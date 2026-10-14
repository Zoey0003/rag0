# RAG 召回、生成与耗时对照实验

独立于应用运行；只读现有 Milvus，不创建集合、不写入资料、不调用 graph2、Tavily 或会话记忆。每个函数均有中文 docstring。

## 比较方法与指标

- BM25：关键词基线；BGE：现有 512 维模型与 HNSW；hybrid：两路检索、RRF(k=100)。
- 可选 hybrid_rerank：融合后前 20 块交给本地 CrossEncoder 重排，最终取 5 块。
- 单路各召回 20 块，最终 Top 5；混合组每路 20 块。候选总预算存在差异，因此混合收益不能单独归因于融合算法。
- Recall@5 = 命中的不同相关块数 / 人工标注相关块总数。MRR@5 = 第一块相关结果的排名倒数，再对题目取平均。额外输出 Hit@5。
- 无相关资料的题目 Recall/MRR 为 N/A，不纳入检索指标均值；可参与生成层评估。
- RAGAS：Faithfulness、Response Relevancy、Factual Correctness(F1)。RAGAS context recall 不替代人工块标注的 Recall@5。
- 计时：编码、数据库请求、重排序、检索总计、生成、端到端；初始化及 RAGAS 调用不计入问答耗时。
- 数据库请求包含网络、服务端检索；hybrid 的请求还包含融合，无法单独报告服务端 RRF 耗时。
- 保存生成输入/输出 Token（供应商未返回时为 null）；本地编码不是在线计费 Token。
- 固定随机种子交错方法顺序，检索预热，默认重复三遍。汇总均值、nearest-rank P50/P95及失败计数。少量题目的 P95 不稳定。

## 1. 导出真实块

打开 Milvus，在内层源码目录执行：

```powershell
conda activate rag0
cd D:\1pyproject\rag0\backend
python -X utf8 -m rag_eval.run export
```

生成 `rag_eval/data/corpus.json`（ID、正文、标题、来源及指纹）。导出拒绝覆盖旧快照。实验期间停止增量导入、上传及重建；代码会检查运行前后版本，但不能替代真正的数据库快照或写入隔离。

## 2. 生成候选标注池

```powershell
python -X utf8 -m rag_eval.run pool
```

输出目录中 `annotation_pool.json` 按题目合并各方法前 20 个候选，正文不按方法高亮。人工阅读候选及 corpus，找出直接支持问题的块，填写 `data/questions.json`：

```json
{
  "id": "dev_001",
  "question": "晶圆级封装为什么能降低成本？",
  "relevant_chunk_ids": ["这里填写真实块ID"],
  "reference": "人工核对后的参考答案，保留原文数值和适用条件。",
  "annotation_complete": true
}
```

初始三个问题没有自动给出答案或正确块。候选池不是全部相关块集合，须检查遗漏资料；报告中说明 pooled judgments 的不完整性。同文件多个块分别标注，不以文件名代替块 ID。正式实验会拒绝未完成标注和不存在的 ID。

这三个题只用于开发。正式评测增加不同主题的题目，开发与测试题分开；对照实验期间不得根据测试结果修改提示词或标注标准。

## 3. 执行对照

只测检索（无需聊天 API）：

```powershell
python -X utf8 -m rag_eval.run run --repeat 3
```

检索加真实模型生成（消耗千问 API Token）：

```powershell
python -X utf8 -m rag_eval.run run --repeat 3 --generate
```

使用项目内层 `.env` 的 `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`，也可先设置环境变量。默认 qwen-plus、temperature=0、关闭 SDK 自动重试。不启用图路由、文档评分、改写或答案重试，以隔离检索方法。

各组使用相同提示和最多 16000 正文字符的预算。这不是精确 Token 预算；实际 Token 记录在结果中。若发生截断，Recall 基于召回 Top 5，RAGAS 基于实际发送的截断上下文。

可选第四组（模型须提前下载到本地，不自动安装或下载）：

```powershell
python -X utf8 -m rag_eval.run run --generate --methods bm25 bge hybrid hybrid_rerank --reranker D:\path\to\cross-encoder
```

重排序模型应输出每个问题/文档对的单个相关性分数，并按其模型卡确认语言、长度和用法；截断受该模型配置影响。没有指定模型时，不会伪造第四组结果。

每次保存独立目录：`metadata.json` 保存配置、题集、版本及指纹，`records.jsonl` 逐条落盘保存召回正文、分数、答案、Token、耗时及错误。三路原始分数不可直接比较。

## 4. RAGAS 生成评估

评估脚本针对固定版本 0.3.8 API 编写，不要求更新主应用依赖。建议克隆环境安装，避免影响现有应用：

```powershell
conda create -n rag_eval --clone rag0
conda activate rag_eval
python -m pip install -r rag_eval/requirements-ragas.txt
python -m pip check
```

指定裁判（填可用模型名，不预设供应商权限）。默认复用百炼地址和密钥，也可以通过 `EVAL_JUDGE_BASE_URL`、`EVAL_JUDGE_API_KEY` 配置独立服务：

```powershell
$env:EVAL_JUDGE_MODEL = '你的裁判模型名称'
python -X utf8 -m rag_eval.evaluate_ragas --run-dir rag_eval/results/实际运行目录
```

Response Relevancy 使用本地 BGE 作为评估 Embedding，所有方法相同。最好使用不同于生成模型的裁判，并抽样人工复核。中文评估效果及模型兼容性需要实际验证。评估有额外 API 成本；耗时记录在 `ragas.json` 的 `metric_seconds`，不混入端到端耗时。失败或非有限分数为 null，并明确保存错误；已有评估文件不会自动覆盖。

参考 API：[RAGAS 0.3.8 metrics](https://docs.ragas.io/en/v0.3.8/references/metrics/)。尚未在本机安装 RAGAS 或执行真实裁判调用。

## 5. 汇总报告

```powershell
python -X utf8 -m rag_eval.run report --run-dir rag_eval/results/实际运行目录
```

输出 `summary.json`（所有指标、样本数及失败计数）和 `summary.md`（主要指标表）。没有 RAGAS 或生成结果时显示 N/A。失败请求的检索分数按零记，生成及裁判指标报告成功样本覆盖数，避免把失败样本默默当作通过。

正式报告需注明题数、标注方式、候选预算、机器 CPU/GPU、模型版本、重复次数及失败率。没有真实实验结果时，不能使用之前讨论的虚构数值。

## 离线验证

```powershell
python -X utf8 -m unittest rag_eval.test_metrics -v
```

仅检查公式、边界、上下文预算与标注门槛，无模型或数据库调用。
