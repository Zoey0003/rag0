"""统一实验配置；密钥仅从环境读取，不写入实验结果。"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env", override=False)
DATA = ROOT / "data"
RESULTS = ROOT / "results"
URI = os.getenv("EVAL_MILVUS_URI", "http://127.0.0.1:19530")
COLLECTION = os.getenv("EVAL_COLLECTION", "t_collection01")
BGE_PATH = os.getenv("EVAL_BGE_PATH", r"D:\1pyproject\rag0\models\bge-small-zh-v1.5")
TOP_K = 5
CANDIDATES = 20
METHODS = ["bm25", "bge", "hybrid"]
GEN_MODEL = os.getenv("EVAL_GEN_MODEL", "qwen-plus")
CONTEXT_CHAR_LIMIT = 16000


def chat_model(judge=False):
    """创建生成或裁判模型；裁判须显式配置，避免无意使用同模型自评分。"""
    from langchain_openai import ChatOpenAI

    model = os.getenv("EVAL_JUDGE_MODEL") if judge else GEN_MODEL
    if not model:
        raise ValueError("请设置 EVAL_JUDGE_MODEL（可与生成模型不同）")
    key = os.getenv("EVAL_JUDGE_API_KEY") if judge else None
    url = os.getenv("EVAL_JUDGE_BASE_URL") if judge else None
    key = key or os.getenv("DASHSCOPE_API_KEY")
    url = url or os.getenv("DASHSCOPE_BASE_URL")
    if not key or not url:
        raise ValueError("请配置 DASHSCOPE_API_KEY 和 DASHSCOPE_BASE_URL 或裁判专用变量")
    return ChatOpenAI(model=model, api_key=key, base_url=url, temperature=0,
                      timeout=120, max_retries=0)
