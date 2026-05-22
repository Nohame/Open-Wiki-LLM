from .search_service import search
from .wiki_service import list_pages
from . import llm_service
from ..models.answer import AnswerRequest, AnswerResponse

FALLBACK = "Je ne trouve pas cette information dans le wiki validé."

ANSWER_PROMPT = """\
Tu es un assistant qui répond à des questions à partir d'extraits de wiki.

Question : {question}

Extraits pertinents du wiki :
{context}

Réponds en te basant uniquement sur ces extraits. Si tu ne peux pas répondre, dis-le clairement.
"""


async def answer(request: AnswerRequest) -> AnswerResponse:
    results = search(request.question, limit=request.limit)

    if request.mode in ("strict", "validated_only"):
        all_pages = list_pages()
        validated_slugs = {p.slug for p in all_pages if p.status == "validated"}
        results = [r for r in results if r.slug in validated_slugs]

    if not results:
        return AnswerResponse(answer=FALLBACK, mode=request.mode, sources=[])

    context = "\n\n".join(f"[{r.title}]\n{r.snippet}" for r in results)
    prompt = ANSWER_PROMPT.format(question=request.question, context=context)
    llm_answer = await llm_service.get_provider().generate(prompt)

    return AnswerResponse(
        answer=llm_answer,
        mode=request.mode,
        sources=[r.slug for r in results],
    )
