from typing import Literal

from pydantic import BaseModel, Field


class CreateMemoryRequest(BaseModel):
    """手动保存长期记忆的请求数据。"""

    content: str = Field(min_length=1, max_length=1000)
    kind: Literal["preference", "fact"] = "preference"
    source_message_id: int | None = Field(default=None, gt=0)