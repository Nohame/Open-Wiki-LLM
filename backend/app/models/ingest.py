from pydantic import BaseModel


class IngestTextRequest(BaseModel):
    text: str
    title: str | None = None
    tags: list[str] = []


class IngestResult(BaseModel):
    slug: str
    raw_path: str
    wiki_path: str
    title: str
    pages_updated: list[str] = []
    concepts_created: list[str] = []
    entities_created: list[str] = []
    stale_marked: list[str] = []
