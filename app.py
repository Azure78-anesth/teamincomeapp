import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Supabase 연결
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]
sdb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="수입 관리", layout="wide")

# -----------------------------
# 유틸 함수
# -----------------------------

def sb_list(name, ym_key=None, year=None, offset=0, batch_size=1000):
    q = sdb.table(name).select("*")

    # incomes 테이블만 연도별 필터 + 페이지네이션
    if name == "incomes" and year:
        q = (
            q.gte("date", f"{year}-01-01")
             .lt("date", f"{year+1}-01-01")
             .order("created_at", desc=True)
             .range(offset, offset + batch_size - 1)
        )
    else:
        q = q.order("created_at", desc=True)

    res = q.execute()
    return getattr(res, "data", None) or []

# -----------------------------
# 연도 선택
# -----------------------------
this_year = datetime.now().year
sel_year = st.sidebar.selectbox("연도 선택", list(range(this_year, this_year-5, -1)), index=0)

# -----------------------------
# 팀원 / 업체 로드 (전체)
# -----------------------------
team_members = sb_list("team_members")
locations = sb_list("locations")

team_names = [m.get("name") for m in team_members]
location_names = [l.get("name") for l in locations]

# -----------------------------
# 수입 입력
# -----------------------------
st.header("수입 입력")
col1, col2 = st.columns(2)
with col1:
    input_date = st.date_input("발생일", datetime.now())
    team_name = st.selectbox("팀원", ["(팀원을 먼저 추가하세요)"] + team_names)
with col2:
    category = st.radio("업체 분류", ["보험", "비보험"], horizontal=True)
    loc_opts = [l for l in location_names if l] or ["(업체를 추가하세요)"]
    location = st.selectbox("업체", loc_opts)

amount = st.number_input("금액(만원 단위)", min_value=0, value=0)

if st.button("등록하기"):
    if not team_name or team_name.startswith("("):
        st.warning("팀원을 먼저 선택하세요.")
    elif not location or location.startswith("("):
        st.warning("업체를 선택하세요.")
    else:
        new_row = {
            "date": input_date.isoformat(),
            "amount": amount,
            "team_member_name": team_name,
            "location_name": location,
            "category": category,
            "created_at": datetime.utcnow().isoformat()
        }
        sdb.table("incomes").insert(new_row).execute()
        st.success(f"{input_date} 수입이 저장되었습니다 ✅")

# -----------------------------
# 조회 (연도별 페이지네이션)
# -----------------------------
st.header(f"{sel_year}년 수입 조회")

# 페이지네이션 설정
page_size = 100
page = st.number_input("페이지", min_value=1, value=1, step=1)
offset = (page - 1) * page_size

incomes = sb_list("incomes", year=sel_year, offset=offset, batch_size=page_size)
if not incomes:
    st.info("해당 연도의 데이터가 없습니다.")
else:
    st.dataframe(incomes)

# -----------------------------
# 간단한 합계 표시
# -----------------------------
total = sum(i.get("amount", 0) or 0 for i in incomes)
st.metric(label=f"{sel_year}년 표시된 페이지 합계", value=f"{total:,.0f} 만원")
