from fastapi import APIRouter
from ..services import wiki_manager
from ..models.log import LogResponse

router = APIRouter(prefix="/api")


@router.get("/wiki/log", response_model=LogResponse)
async def get_log() -> LogResponse:
    return LogResponse(content=wiki_manager.load_log())
