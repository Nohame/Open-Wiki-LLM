from pydantic import BaseModel


class PageReferences(BaseModel):
    slug: str
    references: list[str] = []
    referenced_by: list[str] = []
