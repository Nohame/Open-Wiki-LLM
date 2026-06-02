from fastapi import APIRouter, Depends
from ..services import git_service
from ..core.auth import verify_api_key

router = APIRouter(prefix="/api/git", dependencies=[Depends(verify_api_key)])


@router.get("/status")
def git_status() -> dict:
    return git_service.get_status()


@router.post("/init")
def git_init() -> dict:
    if git_service.is_initialized():
        return {"status": "already_initialized"}
    git_service.init_repo()
    return {"status": "initialized"}


@router.post("/push")
def git_push() -> dict:
    git_service.push()
    return {"status": "push_triggered"}


@router.get("/log")
def git_log(limit: int = 10) -> list[dict]:
    return git_service.get_log(limit=limit)
