from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI


from utils.env_utils import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
llm = ChatOpenAI(
    temperature=0,
    model="qwen-plus",
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
    extra_body={"enable_thinking": False},
)


web_search_tool = TavilySearchResults(max_results=2)

# llm = ChatOpenAI(
#     temperature=0.5,
#     model='deepseek-chat',
#     api_key=DEEPSEEK_API_KEY,
#     base_url="https://api.deepseek.com")