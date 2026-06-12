import asyncio
from fastapi import APIRouter
from pydantic import BaseModel

from services.ontong_api import search_youth_policies
from services.fss_api import search_financial_products
from services.openai_service import generate_response, build_context

router = APIRouter()

YOUTH_KEYWORDS = [
    "정책", "지원", "혜택", "신청", "청년", "취업", "창업", "교육",
    "주거", "생활", "장학", "복지", "바우처", "수당", "일자리",
]
FINANCE_KEYWORDS = [
    "예금", "적금", "대출", "금리", "이자", "금융", "저축", "은행",
    "상품", "이율", "통장", "투자", "자산", "담보", "빌리",
]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class Source(BaseModel):
    name: str
    type: str


class ChatResponse(BaseModel):
    reply: str
    sources: list[Source] = []


def _resolve_targets(query: str) -> tuple[bool, bool]:
    q = query.lower()
    use_ontong = any(kw in q for kw in YOUTH_KEYWORDS)
    use_fss = any(kw in q for kw in FINANCE_KEYWORDS)
    if not use_ontong and not use_fss:
        return True, True
    return use_ontong, use_fss


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    use_ontong, use_fss = _resolve_targets(request.message)

    tasks = []
    if use_ontong:
        tasks.append(("ontong", search_youth_policies(request.message)))
    if use_fss:
        tasks.append(("fss", search_financial_products(request.message)))

    ontong_data = None
    fss_data = None
    sources: list[Source] = []

    if tasks:
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        for i, (api_type, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                continue
            if api_type == "ontong":
                ontong_data = result
                if result.get("youthPolicyList"):
                    sources.append(Source(name="온통청년", type="ontong"))
            elif api_type == "fss":
                fss_data = result
                if result:
                    sources.append(Source(name="금융감독원", type="fss"))

    context = build_context(ontong_data, fss_data)
    history = [{"role": m.role, "content": m.content} for m in request.history]
    reply = await generate_response(request.message, context, history)

    return ChatResponse(reply=reply, sources=sources)
