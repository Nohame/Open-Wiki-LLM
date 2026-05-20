from pydantic import BaseModel
from typing import Literal


class WikiPage(BaseModel):
    slug: str
    title: str
    type: Literal["concept", "project", "procedure", "decision", "note", "entity"] = "note"
    status: Literal["draft", "reviewed", "validated", "deprecated"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    sources: list[str] = []
    updated_at: str = ""
    tags: list[str] = []
    stale: bool = False
    content: str


class StaleUpdate(BaseModel):
    stale: bool
