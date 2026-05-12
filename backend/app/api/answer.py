from fastapi import APIRouter, Depends
from ..services.answer_service import answer
from ..models.answer import AnswerRequest, AnswerResponse
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: AnswerRequest) -> AnswerResponse:
    return await answer(request)
