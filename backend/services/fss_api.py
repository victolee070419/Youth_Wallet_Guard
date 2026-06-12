import httpx
import os
import asyncio

FSS_BASE_URL = "https://finlife.fss.or.kr/finlifeapi"

# 020000=은행, 030300=저축은행
DEFAULT_BANK_CODE = "020000"


async def _fetch(endpoint: str, bank_code: str = DEFAULT_BANK_CODE) -> dict:
    api_key = os.getenv("FSS_API_KEY")
    if not api_key:
        return {}

    params = {"auth": api_key, "topFinGrpNo": bank_code, "pageNo": 1}
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            response = await client.get(f"{FSS_BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}


async def search_financial_products(query: str) -> dict:
    q = query.lower()
    is_loan = any(kw in q for kw in ["대출", "빌리다", "빌려", "담보", "신용대출"])
    is_saving = any(kw in q for kw in ["적금"])
    is_deposit = any(kw in q for kw in ["예금", "정기"])

    tasks = []
    if is_loan:
        tasks.append(("loan", _fetch("loanProductsSearch.json")))
    elif is_saving and not is_deposit:
        tasks.append(("saving", _fetch("savingProductsSearch.json")))
    elif is_deposit and not is_saving:
        tasks.append(("deposit", _fetch("depositProductsSearch.json")))
    else:
        tasks.append(("deposit", _fetch("depositProductsSearch.json")))
        tasks.append(("saving", _fetch("savingProductsSearch.json")))

    results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

    combined = {}
    for i, (product_type, _) in enumerate(tasks):
        result = results[i]
        if not isinstance(result, Exception) and result:
            combined[product_type] = result

    return combined
