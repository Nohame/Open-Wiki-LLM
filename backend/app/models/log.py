from pydantic import BaseModel


class LogResponse(BaseModel):
    content: str
