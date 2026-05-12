from pydantic import BaseModel
from typing import Literal


class AnswerRequest(BaseModel):
    question: str
    mode: Literal["draft", "strict", "source_only", "validated_only"] = "strict"
    limit: int = 5


class AnswerResponse(BaseModel):
    answer: str
    mode: str
    sources: list[str]
