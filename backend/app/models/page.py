from pydantic import BaseModel
from typing import Literal


class WikiPage(BaseModel):
    slug: str
    title: str
    type: Literal["concept", "project", "procedure", "decision", "note"] = "note"
    status: Literal["draft", "reviewed", "validated", "deprecated"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    sources: list[str] = []
    updated_at: str = ""
    tags: list[str] = []
    content: str
