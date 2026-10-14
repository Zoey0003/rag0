"""使用固定 RAGAS 0.3.8 接口，评估耗时与用户问答耗时分离。"""
import argparse
import asyncio
import json
import math
from pathlib import Path
from time import perf_counter

from rag_eval import config as cfg
from rag_eval.common import read_json, write_json


async def evaluate(directory):
    """逐条逐指标评估，保留失败与 NaN，避免将评估失败伪装成零分或通过。"""
    from ragas import SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, FactualCorrectness, ResponseRelevancy
    from langchain_huggingface import HuggingFaceEmbeddings

    directory = Path(directory)
    if (directory / "ragas.json").exists():
        raise ValueError("ragas.json 已存在，请备份后再重新评估")
    metadata = read_json(directory / "metadata.json")
    if metadata.get("corpus_unchanged") is not True or not metadata.get("generation_model"):
        raise ValueError("需要知识库未变化且包含生成结果的正式实验")
    judge = cfg.chat_model(judge=True)
    wrapped = LangchainLLMWrapper(judge)
    embedding = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=cfg.BGE_PATH,
        model_kwargs={"device": "cpu"}, encode_kwargs={"normalize_embeddings": True}))
    metrics = [Faithfulness(llm=wrapped), ResponseRelevancy(llm=wrapped, embeddings=embedding),
               FactualCorrectness(llm=wrapped, mode="f1")]
    rows = [json.loads(line) for line in (directory / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    results = []
    for row in rows:
        if row.get("generation_ok") is not True:
            continue
        item = {"case_id": row["case_id"], "method": row["method"], "repeat": row["repeat"],
                "judge_model": judge.model_name, "scores": {}, "errors": {}, "metric_seconds": {}}
        sample = SingleTurnSample(user_input=row["question"], response=row["response"],
                                  retrieved_contexts=row["retrieved_contexts"], reference=row["reference"])
        for metric in metrics:
            started = perf_counter()
            try:
                score = float(await asyncio.wait_for(metric.single_turn_ascore(sample), timeout=300))
                if not math.isfinite(score):
                    raise ValueError("指标返回 NaN 或无穷值")
                item["scores"][metric.name] = score
            except Exception as exc:
                item["scores"][metric.name] = None
                item["errors"][metric.name] = f"{type(exc).__name__}: {exc}"
            item["metric_seconds"][metric.name] = perf_counter() - started
        results.append(item)
        write_json(directory / "ragas.json", results)
        print(row["case_id"], row["method"], item["scores"])


def main():
    """接收已生成的结果目录；不再次检索或重新生成答案。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    asyncio.run(evaluate(args.run_dir))


if __name__ == "__main__":
    main()
