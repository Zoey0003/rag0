# import os
# from dotenv import load_dotenv
# load_dotenv(override=True)

import os
from pathlib import Path
from dotenv import load_dotenv

# 固定读取 backend/.env，避免受终端工作目录影响。
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH, override=True)



DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

MILVUS_URI = "http://127.0.0.1:19530"
COLLECTION_NAME = 't_collection01'
