from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from utils.env_utils import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
openai_embedding = OpenAIEmbeddings(
    model="text-embedding-v4",
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
    check_embedding_ctx_length=False,
    chunk_size=10,
)

model_name = r"D:\1pyproject\rag0\models\bge-small-zh-v1.5"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}
bge_embedding = HuggingFaceEmbeddings(
    model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
)