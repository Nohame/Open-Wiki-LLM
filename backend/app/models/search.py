from pydantic import BaseModel


class SearchQuery(BaseModel):
    q: str
    limit: int = 10


class SearchResult(BaseModel):
    slug: str
    title: str
    snippet: str
    score: float
