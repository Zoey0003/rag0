"""数据读写与指标：保持无网络依赖，方便离线测试。"""
import hashlib
import json
import math
from pathlib import Path


def read_json(path):
    """读取 UTF-8 JSON，也兼容编辑器保存的 BOM。"""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    """以 UTF-8 保存真实结果；拒绝将 NaN 等非标准值写入文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def fingerprint(chunks):
    """按主键排序后计算正文和元数据指纹，检测重建、增量写入或资料变化。"""
    raw = json.dumps(sorted(chunks, key=lambda c: c["id"]), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def retrieval_metrics(ranked_ids, relevant_ids, k=5):
    """计算 Recall@K、MRR@K 和 Hit@K；无相关标注时记空值，不伪造满分。"""
    gold = set(map(str, relevant_ids))
    if not gold:
        return {"recall5": None, "mrr5": None, "hit5": None}
    # 同一块重复出现不能重复计分，也不能占据两个排名。
    ranked = list(dict.fromkeys(map(str, ranked_ids)))[:k]
    first = next((i for i, value in enumerate(ranked, 1) if value in gold), None)
    return {"recall5": len(set(ranked) & gold) / len(gold),
            "mrr5": 1 / first if first else 0.0, "hit5": float(first is not None)}


def stats(values):
    """汇总有限数值，P50/P95 使用 nearest-rank 定义，空数据不记为零。"""
    values = sorted(float(v) for v in values if v is not None and math.isfinite(v))
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p95": None}
    return {"n": len(values), "mean": sum(values) / len(values),
            "p50": values[math.ceil(len(values) * .5) - 1],
            "p95": values[math.ceil(len(values) * .95) - 1]}


def validate_cases(cases, corpus, annotated=True):
    """校验题目唯一性、相关块存在性与人工标注确认，防止示例被当作正式评测。"""
    if not isinstance(cases, list) or not cases:
        raise ValueError("题集必须是非空列表")
    ids = set()
    known = {c["id"] for c in corpus}
    for case in cases:
        if not isinstance(case.get("id"), str) or case["id"] in ids:
            raise ValueError("题目 ID 必须是唯一字符串")
        ids.add(case["id"])
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError(f"{case['id']} 的问题为空")
        gold = case.get("relevant_chunk_ids", [])
        if not isinstance(gold, list) or not all(isinstance(v, str) for v in gold):
            raise ValueError("relevant_chunk_ids 必须是字符串列表")
        if set(gold) - known:
            raise ValueError(f"{case['id']} 的相关块不在当前快照中")
        if annotated and (case.get("annotation_complete") is not True or not case.get("reference", "").strip()):
            raise ValueError(f"{case['id']} 需要完成人工标注、参考答案并设置 annotation_complete=true")
