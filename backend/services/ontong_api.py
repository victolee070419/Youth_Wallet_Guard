import httpx
import os

ONTONG_BASE_URL = "https://www.youthcenter.go.kr/go/opi/youthPlcyList.do"


async def search_youth_policies(query: str, page: int = 1, display: int = 5) -> dict:
    api_key = os.getenv("ONTONG_API_KEY")
    if not api_key:
        return {"youthPolicyList": [], "error": "API key not configured"}

    params = {
        "openApiVlak": api_key,
        "srchName": query,
        "pageIndex": page,
        "display": display,
        "returnType": "JSON",
    }

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
        try:
            response = await client.get(ONTONG_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"youthPolicyList": [], "error": "요청 시간이 초과되었습니다"}
        except Exception as e:
            return {"youthPolicyList": [], "error": str(e)}
