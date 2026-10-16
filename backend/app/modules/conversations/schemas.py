from pydantic import BaseModel, Field


class CreateMemorySessionRequest(BaseModel):
    """新建会话的请求数据。"""

    title: str = Field(
        default="新对话",
        min_length=1,
        max_length=200,
    )


class RenameMemorySessionRequest(BaseModel):
    """重命名会话的请求数据。"""

    title: str = Field(
        min_length=1,
        max_length=200,
    )