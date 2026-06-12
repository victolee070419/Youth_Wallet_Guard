from __future__ import annotations

import httpx
import os

BASE_URL = "https://www.youthcenter.go.kr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": BASE_URL + "/",
}


async def _get_guest_token() -> str:
    """메인 페이지를 방문해 게스트 JWT(ygt) 쿠키를 발급받습니다."""
    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(BASE_URL + "/")
        for cookie in client.cookies.jar:
            if cookie.name == "ygt":
                return cookie.value
        # 응답 헤더에서도 시도
        for h in resp.headers.get_list("set-cookie"):
            if "ygt=" in h:
                return h.split("ygt=")[1].split(";")[0]
    return ""


async def search_youth_policies(query: str, page: int = 1, display: int = 5) -> dict:
    """온통청년 내부 API로 청년 정책을 키워드 검색합니다."""
    try:
        token = await _get_guest_token()
        if not token:
            return {"youthPolicyList": [], "error": "게스트 토큰 발급 실패"}

        headers = {**HEADERS, "Content-Type": "application/json"}
        cookies = {"ygt": token}
        payload = {
            "plcyReq": {
                "useYn": "Y",
                "plcyAprvSttsCd": "0044002",
                "srchKeyword": query,
            },
            "paggingVO": {"pageNum": page, "pageSize": display},
        }

        async with httpx.AsyncClient(timeout=20.0, headers=headers, cookies=cookies) as client:
            resp = await client.post(
                BASE_URL + "/wrk/yrm/plcyInfo/selectPlcy",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_list = data.get("result", {}).get("plcyList", [])

        # 필드 정규화 (기존 코드와 호환되는 youthPolicyList 형식으로 변환)
        normalized = []
        for p in raw_list:
            normalized.append({
                "polyBizSjnm": p.get("plcyNm", ""),
                "sporCn": p.get("plcyExplnCn", ""),
                "ageInfo": f"{p.get('sprtTrgtMinAge', '')}~{p.get('sprtTrgtMaxAge', '')}세"
                           if p.get("sprtTrgtMinAge") else "",
                "prcpCn": p.get("userLclsfNm", ""),
                "rqutPrdCn": p.get("aplyPrdSttsCstmNo", ""),
                "polyBizTy": p.get("rgtrUpInstCdNm", ""),
                "region": p.get("stdgCtpvSggCdList", ""),
                "keyword": p.get("plcyKywdNm", ""),
            })

        return {"youthPolicyList": normalized}

    except httpx.TimeoutException:
        return {"youthPolicyList": [], "error": "요청 시간 초과"}
    except Exception as e:
        return {"youthPolicyList": [], "error": str(e)}
