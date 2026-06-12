from __future__ import annotations

from openai import AsyncOpenAI
import os
from typing import Optional

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """당신은 'Wallet Guard'라는 청년 금융 및 정책 정보 도우미입니다.

데이터 소스:
1. 온통청년 (youthcenter.go.kr): 청년 지원 정책, 혜택, 자격 요건
2. 금융감독원 (fss.or.kr): 예금·적금·대출 금융 상품 비교 정보

답변 규칙:
- 제공된 API 데이터를 최우선으로 활용하세요
- 금리·지원금액 등 구체적 수치는 반드시 출처를 언급하세요
- 정보가 없는 경우 솔직하게 알려주세요
- 한국어로 친절하고 명확하게 답변하세요
- 중요 정보는 불릿(•) 또는 번호 목록으로 구조화하세요
- 답변 마지막에 신청 방법이나 추가 정보 확인처를 안내해주세요"""


def _format_ontong(data: dict) -> str:
    policies = data.get("youthPolicyList", [])
    if not policies:
        return ""

    lines = ["[온통청년 정책 정보]"]
    for i, p in enumerate(policies[:5], 1):
        name = p.get("polyBizSjnm", "")
        support = p.get("sporCn", "")
        age = p.get("ageInfo", "")
        period = p.get("rqutPrdCn", "")
        condition = p.get("prcpCn", "")

        lines.append(f"\n{i}. {name}")
        if support:
            lines.append(f"   지원내용: {support[:300]}")
        if age:
            lines.append(f"   지원연령: {age}")
        if period:
            lines.append(f"   신청기간: {period[:100]}")
        if condition:
            lines.append(f"   참여요건: {condition[:200]}")

    return "\n".join(lines)


def _format_fss(data: dict) -> str:
    if not data:
        return ""

    type_labels = {"deposit": "정기예금", "saving": "적금", "loan": "대출"}
    lines = ["[금융감독원 금융상품 정보]"]

    for product_type, raw in data.items():
        result = raw.get("result", {})
        base_list = result.get("baseList", [])
        option_list = result.get("optionList", [])
        if not base_list:
            continue

        option_map: dict[str, list] = {}
        for opt in option_list:
            key = f"{opt.get('fin_co_no')}_{opt.get('fin_prdt_cd')}"
            option_map.setdefault(key, []).append(opt)

        label = type_labels.get(product_type, product_type)
        lines.append(f"\n[{label} 상품 TOP 5]")

        for p in base_list[:5]:
            bank = p.get("kor_co_nm", "")
            name = p.get("fin_prdt_nm", "")
            join_way = p.get("join_way", "")
            join_member = p.get("join_member", "")

            lines.append(f"  • {bank} | {name}")
            if join_way:
                lines.append(f"    가입방법: {join_way}")
            if join_member:
                lines.append(f"    가입대상: {join_member[:80]}")

            key = f"{p.get('fin_co_no')}_{p.get('fin_prdt_cd')}"
            for opt in option_map.get(key, [])[:3]:
                trm = opt.get("save_trm", "")
                rate = opt.get("intr_rate", "")
                rate2 = opt.get("intr_rate2", "")
                rate_type = opt.get("intr_rate_type_nm", "")
                if trm and rate:
                    lines.append(
                        f"    {trm}개월({rate_type}): 기본 {rate}% / 최고 {rate2}%"
                    )

    return "\n".join(lines)


def build_context(ontong_data: dict | None, fss_data: dict | None) -> str:
    parts = []
    if ontong_data:
        ctx = _format_ontong(ontong_data)
        if ctx:
            parts.append(ctx)
    if fss_data:
        ctx = _format_fss(fss_data)
        if ctx:
            parts.append(ctx)
    return "\n\n".join(parts)


async def generate_response(
    user_message: str,
    context: str,
    chat_history: list[dict],
) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(chat_history[-10:])

    if context:
        content = f"다음 데이터를 참고하여 질문에 답해주세요:\n\n{context}\n\n질문: {user_message}"
    else:
        content = user_message

    messages.append({"role": "user", "content": content})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )
    return response.choices[0].message.content
