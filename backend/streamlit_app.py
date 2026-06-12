import streamlit as st
import asyncio
import os
import sys
import concurrent.futures

# backend 디렉토리가 import 경로에 있도록 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 로컬: .env / Streamlit Cloud: st.secrets
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    for key in ["ONTONG_API_KEY", "FSS_API_KEY", "OPENAI_API_KEY"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass

from services.ontong_api import search_youth_policies
from services.fss_api import search_financial_products
from services.openai_service import generate_response, build_context

# ── 라우팅 로직 ─────────────────────────────────────────────

YOUTH_KEYWORDS = [
    "정책", "지원", "혜택", "신청", "청년", "취업", "창업", "교육",
    "주거", "생활", "장학", "복지", "바우처", "수당", "일자리",
]
FINANCE_KEYWORDS = [
    "예금", "적금", "대출", "금리", "이자", "금융", "저축", "은행",
    "상품", "이율", "통장", "투자", "자산", "담보", "빌리",
]
ONTONG_SEARCH_TERMS = [
    "주거", "취업", "창업", "교육", "장학", "복지", "수당", "바우처",
    "일자리", "훈련", "직업", "청년", "임대", "전세", "월세", "금융",
    "저축", "적금", "대출", "생활비", "심리", "상담", "건강",
]


def _resolve_targets(query: str):
    q = query.lower()
    use_ontong = any(kw in q for kw in YOUTH_KEYWORDS)
    use_fss = any(kw in q for kw in FINANCE_KEYWORDS)
    if not use_ontong and not use_fss:
        return True, True
    return use_ontong, use_fss


def _extract_search_keyword(query: str) -> str:
    for term in ONTONG_SEARCH_TERMS:
        if term in query:
            return term
    words = query.replace("?", "").replace(".", "").split()
    return " ".join(words[:2]) if words else query


# ── 비동기 처리 ──────────────────────────────────────────────

async def _process(user_message: str, history: list, api_key: str = "") -> tuple[str, list]:
    use_ontong, use_fss = _resolve_targets(user_message)

    tasks = []
    if use_ontong:
        tasks.append(("ontong", search_youth_policies(_extract_search_keyword(user_message))))
    if use_fss:
        tasks.append(("fss", search_financial_products(user_message)))

    ontong_data = fss_data = None
    sources = []

    if tasks:
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        for i, (api_type, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                continue
            if api_type == "ontong":
                ontong_data = result
                if result.get("youthPolicyList"):
                    sources.append("온통청년")
            elif api_type == "fss":
                fss_data = result
                if result:
                    sources.append("금융감독원")

    context = build_context(ontong_data, fss_data)
    reply = await generate_response(user_message, context, history, api_key=api_key)
    return reply, sources


def process_message(user_message: str, history: list, api_key: str = "") -> tuple[str, list]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, _process(user_message, history, api_key))
        return future.result()


# ── Streamlit UI ─────────────────────────────────────────────

st.set_page_config(
    page_title="Wallet Guard",
    page_icon="🛡️",
    layout="centered",
)

# ── 사이드바: OpenAI API 키 입력 ─────────────────────────────
with st.sidebar:
    st.markdown("## 🔑 OpenAI API 키")
    st.caption("직접 발급받은 키를 입력하세요. 키는 서버에 저장되지 않습니다.")
    user_api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-proj-...",
        label_visibility="collapsed",
    )
    if user_api_key:
        st.success("키가 입력되었습니다.")
    else:
        st.warning("API 키를 입력해야 채팅이 가능합니다.")
    st.divider()
    st.markdown("**OpenAI API 키 발급**")
    st.markdown("[platform.openai.com](https://platform.openai.com/api-keys) 에서 발급")
    st.divider()
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "안녕하세요! 저는 **Wallet Guard**입니다.\n\n"
                    "**온통청년**과 **금융감독원** 데이터를 기반으로 "
                    "청년 정책 및 금융 상품 정보를 안내해 드립니다.\n\n"
                    "💬 예시 질문:\n"
                    "- 청년 주거 지원 정책이 뭐가 있나요?\n"
                    "- 금리 높은 적금 상품 추천해주세요\n"
                    "- 청년 창업 지원 프로그램 알려주세요"
                ),
                "sources": [],
            }
        ]
        st.rerun()


st.markdown("""
<style>
[data-testid="stChatMessage"] { border-radius: 12px; margin-bottom: 4px; }
.source-tag { display:inline-block; font-size:12px; font-weight:600;
              padding:2px 10px; border-radius:10px; margin:2px; }
.tag-ontong { background:#e8f5e9; color:#2e7d32; border:1px solid #81c784; }
.tag-fss    { background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }
</style>
""", unsafe_allow_html=True)

# 헤더
col1, col2 = st.columns([3, 2])
with col1:
    st.markdown("## 🛡️ Wallet Guard")
    st.caption("청년 금융 & 정책 정보 도우미")
with col2:
    st.markdown(
        '<div style="text-align:right;padding-top:20px">'
        '<span class="source-tag tag-ontong">온통청년</span>'
        '<span class="source-tag tag-fss">금융감독원</span>'
        "</div>",
        unsafe_allow_html=True,
    )
st.divider()

# 세션 초기화
if "show_profile_form" not in st.session_state:
    st.session_state.show_profile_form = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요! 저는 **Wallet Guard**입니다.\n\n"
                "**온통청년**과 **금융감독원** 데이터를 기반으로 "
                "청년 정책 및 금융 상품 정보를 안내해 드립니다.\n\n"
                "💬 예시 질문:\n"
                "- 청년 주거 지원 정책이 뭐가 있나요?\n"
                "- 금리 높은 적금 상품 추천해주세요\n"
                "- 청년 창업 지원 프로그램 알려주세요"
            ),
            "sources": [],
        }
    ]

# 메시지 출력
for msg in st.session_state.messages:
    avatar = "🛡️" if msg["role"] == "assistant" else "🙋"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("sources"):
            tags = "".join(
                f'<span class="source-tag tag-{"ontong" if s == "온통청년" else "fss"}">{s}</span>'
                for s in msg["sources"]
            )
            st.markdown(f'<div style="margin-top:6px">출처: {tags}</div>', unsafe_allow_html=True)

# 제안 버튼
suggestions = ["청년 주거 지원 정책", "금리 높은 적금 추천", "청년 창업 지원", "정기예금 비교"]
cols = st.columns(len(suggestions) + 1)
for col, sug in zip(cols[:-1], suggestions):
    if col.button(sug, use_container_width=True):
        st.session_state.pending_input = sug
        st.session_state.show_profile_form = False
        st.rerun()
if cols[-1].button("🎯 내 맞춤 정책", use_container_width=True):
    st.session_state.show_profile_form = not st.session_state.show_profile_form
    st.rerun()

# 맞춤 정책 폼
if st.session_state.show_profile_form:
    with st.container(border=True):
        st.markdown("#### 🎯 내 맞춤 정책 찾기")
        st.caption("정보를 입력하면 나에게 딱 맞는 정책과 금융 상품을 추천해드립니다.")

        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input("나이", min_value=15, max_value=39, value=25, step=1)
            region = st.selectbox("거주 지역", [
                "전국", "서울", "경기", "인천", "부산", "대구",
                "광주", "대전", "울산", "세종", "강원",
                "충북", "충남", "전북", "전남", "경북", "경남", "제주",
            ])
            housing = st.selectbox("거주 형태", [
                "월세", "전세", "자가", "기숙사/청년 시설", "부모님과 함께",
            ])
        with c2:
            employment = st.selectbox("현재 상태", [
                "취업 준비 중 (구직)", "재직 중 (직장인)",
                "창업 준비 중", "대학(원)생", "프리랜서/자영업",
            ])
            income = st.selectbox("월 소득 수준", [
                "없음 (무직/학생)", "100만원 미만",
                "100~200만원", "200~300만원", "300만원 이상",
            ])
            interests = st.multiselect(
                "관심 분야 (복수 선택)",
                ["주거 지원", "취업/일자리", "창업", "교육/훈련",
                 "금융 (예적금/대출)", "생활비 지원", "심리/건강"],
                default=["주거 지원", "금융 (예적금/대출)"],
            )

        if st.button("맞춤 정책 추천받기 →", type="primary", use_container_width=True):
            interest_str = ", ".join(interests) if interests else "청년 지원 전반"
            query = (
                f"나는 {age}세 청년이고 {region}에 살고 있어. "
                f"거주 형태는 {housing}이고, 현재 상태는 {employment}야. "
                f"월 소득은 {income}이고, 관심 있는 분야는 {interest_str}이야. "
                f"내 상황에 맞는 청년 지원 정책과 금융 상품을 구체적으로 추천해줘."
            )
            st.session_state.pending_input = query
            st.session_state.show_profile_form = False
            st.rerun()

# 채팅 입력
user_input = st.chat_input("청년 정책이나 금융 상품에 대해 물어보세요…")

# 제안 버튼 클릭 처리
if "pending_input" in st.session_state:
    user_input = st.session_state.pop("pending_input")

if user_input:
    if not user_api_key:
        st.warning("왼쪽 사이드바에 OpenAI API 키를 먼저 입력해주세요.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input, "sources": []})
    with st.chat_message("user", avatar="🙋"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🛡️"):
        with st.spinner("검색 중..."):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
                if m["role"] in ("user", "assistant")
            ]
            reply, sources = process_message(user_input, history[-10:], api_key=user_api_key)

        st.markdown(reply)
        if sources:
            tags = "".join(
                f'<span class="source-tag tag-{"ontong" if s == "온통청년" else "fss"}">{s}</span>'
                for s in sources
            )
            st.markdown(f'<div style="margin-top:6px">출처: {tags}</div>', unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})
