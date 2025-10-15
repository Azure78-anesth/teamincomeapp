import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any


# ─────────────────────────────────────────
# Global: 한국 시간 오늘
# ─────────────────────────────────────────
NOW_KST = datetime.now(ZoneInfo("Asia/Seoul"))

# ============================
# Page & Styles (모바일 세로보기 최적화)
# ============================
st.set_page_config(
    page_title="팀 수입 관리",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
:root{
  --bg:#ffffff; --text:#111827; --muted:#6b7280; --border:#e5e7eb; --soft:#f8fafc;
  --brand:#2563eb; --brand-weak:#dbeafe;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0b0f14; --text:#e5e7eb; --muted:#9ca3af; --border:#1f2937; --soft:#0f141b;
    --brand:#3b82f6; --brand-weak:#0b1a33;
  }
}

html, body, [class*="css"] { font-size: 16px; color: var(--text); background: var(--bg); }
section.main > div { padding-top: .6rem; }
h1,h2,h3 { letter-spacing:.2px; margin-top:.25rem; margin-bottom:.5rem; }

.block{
  padding: 1rem 1.1rem; border: 1px solid var(--border);
  border-radius: 14px; background: var(--bg); box-shadow: 0 1px 0 rgba(0,0,0,.03);
}

.stTabs [role="tablist"]{ gap:.25rem; margin-bottom:.25rem; }
.stTabs [role="tab"]{ padding:.45rem .7rem; border-radius:10px; border:1px solid var(--border) !important; }
.stTabs [aria-selected="true"]{ background: var(--brand-weak); border-color: var(--brand) !important; }

button[kind], .stButton>button{
  min-height: 44px; border-radius: 12px; border:1px solid var(--border); font-weight:600;
}
.stTextInput input, .stSelectbox > div, .stDateInput input, .stNumberInput input{
  min-height: 44px; border-radius: 12px !important;
}
.stRadio > div{ gap:.5rem; }

div[data-testid="stDataFrame"]{
  border:1px solid var(--border); border-radius:12px; overflow:hidden;
}
div[data-testid="stDataFrame"] thead th{
  background: var(--soft) !important; position: sticky; top:0; z-index:2;
  border-bottom:1px solid var(--border) !important;
}
.dataframe td, .dataframe th{ white-space: nowrap; }
div[data-testid="stDataFrame"] tbody tr:nth-child(even){
  background: color-mix(in srgb, var(--soft) 60%, transparent);
}

.stMetric{ padding:.5rem .75rem; border:1px solid var(--border); border-radius:12px; background:var(--bg); }
.stMetric-label{ color:var(--muted); font-size:.92rem; }
.stMetric-value{ font-size:1.25rem; }
.stAlert{ border-radius:12px; }
hr, .stDivider{ margin:.75rem 0; }
.mono{ font-variant-numeric: tabular-nums; }

/* 모바일: 표 폰트 조금 축소 + 높이 제한 (컬럼 강제 세로 스택은 제거) */
@media (max-width: 640px){
  body, [class*="css"]{ font-size: 15.5px; }
  .stTabs [role="tab"]{ font-size:.95rem; padding:.4rem .55rem; }
  .stMetric-value{ font-size:1.1rem; }
  .stMetric{ padding:.45rem .6rem; }
  div[data-testid="stDataFrame"] *{ font-size:.95rem; }
  div[data-testid="stDataFrame"]{ max-height: 440px; }
}
@media (max-width: 380px){
  body, [class*="css"]{ font-size: 15px; }
  .stTabs [role="tab"]{ font-size:.9rem; padding:.35rem .5rem; }
}

/* ───────── 설정 탭(팀원/업체)용: 가로 정렬 강제 & 버튼 고정 크기 ───────── */
.manage-inline [data-testid="stHorizontalBlock"]{
  display:flex !important; flex-wrap:nowrap !important; gap:.5rem !important;
}
.manage-inline [data-testid="column"]{
  width:auto !important; flex:0 0 auto !important;
}
.manage-inline .name-col{ min-width:160px; flex:1 1 auto !important; }

.manage-inline .stButton{ width:auto !important; display:inline-block !important; }
.manage-inline .stButton > button,
.manage-inline button[kind],
.manage-inline [data-testid="baseButton-secondary"],
.manage-inline [data-testid="baseButton-primary"]{
  display:inline-flex !important; align-items:center; justify-content:center;
  width:48px !important; min-width:48px !important;
  height:36px !important; padding:6px 0 !important; border-radius:10px;
}

.manage-inline .hdr{ font-weight:700; margin-bottom:6px; }
.manage-inline .row{ display:flex; align-items:center; gap:.5rem; margin:.25rem 0; }

/* ───────── 요약 카드(모바일 2열 그리드) ───────── */
.mgrid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
@media (max-width: 380px){ .mgrid { grid-template-columns:1fr; } }
.mcard { padding:10px 12px; border:1px solid var(--border); border-radius:12px; background: var(--bg); }
.mtitle { color: var(--muted); font-size:.92rem; margin-bottom:4px; }
.mvalue { font-size:1.25rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ============================
# Helpers
# ============================
def metric_cards(items: list[tuple[str, str]]):
    """모바일 친화 요약 카드 (2열 그리드) — 들여쓰기 제거 버전"""
    parts = ['<div class="mgrid">']
    for title, value in items:
        parts.append(f'<div class="mcard"><div class="mtitle">{title}</div><div class="mvalue">{value}</div></div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)

# ============================
# Supabase (옵션)
# ============================
def get_supabase_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
    except Exception:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        st.warning("Supabase 클라이언트를 불러오지 못해 세션 메모리로 동작합니다. (requirements 설치 필요)")
        return None

sb = get_supabase_client()

# ============================
# State & "DB"
# ============================
def init_state():
    if "team_members" not in st.session_state:
        st.session_state.team_members = [
            {"id":"1","name":"김철수","order":0},
            {"id":"2","name":"이영희","order":1},
        ]
    if "locations" not in st.session_state:
        st.session_state.locations = [
            {"id":"l1","name":"서울A치과","category":"보험","order":0},
            {"id":"l2","name":"서울B치과","category":"비보험","order":1},
        ]
    if "income_records" not in st.session_state:
        st.session_state.income_records = []

def load_data():
    if sb:
        try:
            tmem = sb.table("team_members").select("*").order("order").execute().data
            locs = sb.table("locations").select("*").order("order").execute().data
            incs = sb.table("incomes").select("*").order("date").execute().data
            st.session_state.team_members = [{"id":x["id"],"name":x["name"],"order":x.get("order",0)} for x in tmem]
            st.session_state.locations = [{"id":x["id"],"name":x["name"],"category":x.get("category",""),"order":x.get("order",0)} for x in locs]
            st.session_state.income_records = [{
                "id": x["id"], "date": x["date"],
                "teamMemberId": x.get("team_member_id"),
                "locationId": x.get("location_id"),
                "amount": float(x["amount"]),
                "memo": x.get("memo",""),
            } for x in incs]
        except Exception:
            st.warning("오프라인(또는 Supabase 오류) 감지 → 임시 메모리 모드로 전환합니다.")
            init_state()
    else:
        init_state()

def upsert_row(table: str, payload: Dict[str, Any]):
    if sb:
        try:
            if table == "incomes":
                sb.table("incomes").insert({
                    "id": payload["id"], "date": payload["date"],
                    "team_member_id": payload["teamMemberId"],
                    "location_id": payload["locationId"],
                    "amount": payload["amount"], "memo": payload.get("memo",""),
                }).execute()
            elif table == "team_members":
                sb.table("team_members").insert({
                    "id": payload["id"], "name": payload["name"], "order": payload.get("order",0),
                }).execute()
            elif table == "locations":
                sb.table("locations").insert({
                    "id": payload["id"], "name": payload["name"],
                    "category": payload["category"], "order": payload.get("order",0),
                }).execute()
            load_data(); return
        except Exception:
            st.warning("Supabase 기록 실패(오프라인?) → 임시 메모리에 저장합니다.")
    if table == "incomes": st.session_state.income_records.append(payload)
    elif table == "team_members": st.session_state.team_members.append(payload)
    elif table == "locations": st.session_state.locations.append(payload)

def update_income(id_value: str, payload: dict):
    if sb:
        try:
            sb.table("incomes").update({
                "date": payload["date"], "team_member_id": payload["teamMemberId"],
                "location_id": payload["locationId"], "amount": payload["amount"],
                "memo": payload.get("memo",""),
            }).eq("id", id_value).execute()
            load_data(); return
        except Exception:
            st.warning("Supabase 업데이트 실패(오프라인?) → 임시 메모리에만 반영합니다.")
    for r in st.session_state.income_records:
        if r["id"] == id_value:
            r.update({
                "date": payload["date"], "teamMemberId": payload["teamMemberId"],
                "locationId": payload["locationId"], "amount": float(payload["amount"]),
                "memo": payload.get("memo",""),
            }); break

def delete_row(table: str, id_value: str):
    if sb:
        try:
            sb.table(table).delete().eq("id", id_value).execute()
            load_data(); return
        except Exception:
            st.warning("Supabase 삭제 실패(오프라인?) → 임시 메모리에서만 삭제합니다.")
    if table == "incomes":
        st.session_state.income_records = [r for r in st.session_state.income_records if r["id"] != id_value]
    elif table == "team_members":
        st.session_state.team_members = [r for r in st.session_state.team_members if r["id"] != id_value]
    elif table == "locations":
        st.session_state.locations = [r for r in st.session_state.locations if r["id"] != id_value]

def ensure_order(list_key: str):
    lst = st.session_state.get(list_key, [])
    lst_sorted = sorted(lst, key=lambda x: x.get("order", 0))
    changed = False
    for i, x in enumerate(lst_sorted):
        if x.get("order") != i: x["order"] = i; changed = True
    st.session_state[list_key] = lst_sorted
    if changed and sb:
        table = "team_members" if list_key == "team_members" else "locations"
        try:
            for x in lst_sorted:
                sb.table(table).update({"order": x["order"]}).eq("id", x["id"]).execute()
        except Exception:
            st.warning(f"{table} order 정규화 저장 실패(네트워크/권한)")

def swap_order(list_key: str, idx_a: int, idx_b: int):
    lst = st.session_state[list_key]
    a, b = lst[idx_a], lst[idx_b]
    a["order"], b["order"] = b.get("order",0), a.get("order",0)
    st.session_state[list_key] = sorted(lst, key=lambda x: x["order"])
    if sb:
        table = "team_members" if list_key == "team_members" else "locations"
        try:
            sb.table(table).update({"order": a["order"]}).eq("id", a["id"]).execute()
            sb.table(table).update({"order": b["order"]}).eq("id", b["id"]).execute()
        except Exception:
            st.warning("순서 저장 실패(네트워크/권한)")
    load_data(); ensure_order(list_key); st.rerun()

# ============================
# Bootstrapping
# ============================
st.title("팀 수입 관리")
if sb: st.success("✅ Supabase 연결됨 (팀 공동 사용 가능)")
else: st.info("🧪 Supabase 미설정 — 세션 메모리로 동작합니다. 팀 사용은 Secrets에 SUPABASE 설정하세요.")

load_data(); ensure_order("team_members"); ensure_order("locations")

st.session_state.setdefault("confirm_target", None)
st.session_state.setdefault("confirm_action", None)
st.session_state.setdefault("edit_income_id", None)
st.session_state.setdefault("confirm_delete_income_id", None)
st.session_state.setdefault("records_page", 0)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["수입 입력", "통계", "설정", "기록 관리", "정산"])

# ============================
# Tab 1: 수입 입력 (최종 완성 - 오늘 기본 + 다른 날짜 입력 가능)
# ============================
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
NOW_KST = datetime.now(KST)

with tab1:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("수입 입력")

    col1, col2 = st.columns([1, 1])

    with col1:
        # ✅ 한국 시간 기준 오늘 날짜를 항상 계산
        today_kst = datetime.now(KST).date()

        # ✅ 발생일 입력 (항상 오늘이 기본값)
        d = st.date_input(
            "발생일",
            value=today_kst,
            format="YYYY-MM-DD"
        )

        # 팀원 선택
        member_options = {m["name"]: m["id"] for m in st.session_state.team_members}
        member_name = st.selectbox(
            "팀원",
            list(member_options.keys()) if member_options else ["(팀원을 먼저 추가하세요)"]
        )
        member_id = member_options.get(member_name)

    with col2:
        # 보험/비보험 분류
        cat = st.radio("업체 분류", ["보험", "비보험"], horizontal=True)
        filtered_locations = [l for l in st.session_state.locations if l["category"] == cat]
        loc_options = {l["name"]: l["id"] for l in filtered_locations}

        if not loc_options:
            st.warning(f"'{cat}' 분류 업체가 없습니다. 설정 탭에서 추가하세요.")
        loc_name = st.selectbox("업체", list(loc_options.keys()) if loc_options else [])
        loc_id = loc_options.get(loc_name)

    # 금액 입력
    amount_raw = st.text_input("금액(만원 단위)", value="", placeholder="예: 50 (만원)")
    try:
        amount = float(amount_raw.replace(",", "").strip()) if amount_raw.strip() != "" else None
    except ValueError:
        amount = None
        st.error("금액은 숫자만 입력하세요. (예: 50)")

    # ✅ 등록 버튼
    if st.button("등록하기", type="primary"):
        if not (member_id and loc_id and d and (amount is not None and amount > 0)):
            st.error("모든 필드를 올바르게 입력하세요.")
        else:
            rid = f"inc_{datetime.utcnow().timestamp()}"

            # ✅ DB에 입력 (사용자가 선택한 날짜 그대로 저장)
            upsert_row("incomes", {
                "id": rid,
                "date": d.strftime("%Y-%m-%d"),
                "teamMemberId": member_id,
                "locationId": loc_id,
                "amount": float(amount),
            })

            st.success(f"{d.strftime('%Y-%m-%d')} 수입이 저장되었습니다 ✅")

    # ✅ 최근 입력 내역 (미리보기)
    if st.session_state.income_records:
        st.markdown("#### 최근 입력")
        recent = sorted(st.session_state.income_records, key=lambda x: x["date"], reverse=True)[:50]

        df_prev = pd.DataFrame([
            {
                "날짜": r["date"],
                "팀원": next((m["name"] for m in st.session_state.team_members if m["id"] == r["teamMemberId"]), ""),
                "업체": next((l["name"] for l in st.session_state.locations if l["id"] == r["locationId"]), ""),
                "금액(만원)": r["amount"],
            } for r in recent
        ])

        st.dataframe(
            df_prev,
            use_container_width=True,
            column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")}
        )

    st.markdown('</div>', unsafe_allow_html=True)







# ============================
# Tab 2: 통계 (요약 카드 + 상세)
# ============================
with tab2:
    st.markdown('### 통계')

    # ── ID -> 이름 헬퍼
    def _name_from(_id: str, coll: list[dict]) -> str:
        for x in coll:
            if x.get('id') == _id:
                return x.get('name', '')
        return ''

    # ── 원천 데이터 → DF
    records = st.session_state.get('income_records', [])
    if not records:
        st.info('데이터가 없습니다. 먼저 [수입 입력]에서 데이터를 추가해 주세요.')
        st.stop()

    df = pd.DataFrame([{
        'date': r.get('date'),
        'amount': r.get('amount'),
        'member': _name_from(r.get('teamMemberId',''), st.session_state.team_members),
        'location': _name_from(r.get('locationId',''), st.session_state.locations),
        'category': next((l.get('category') for l in st.session_state.locations if l.get('id') == r.get('locationId')), ''),
        'memo': r.get('memo',''),
    } for r in records])

    # ── 정규화
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date']).copy()
    df['year']  = df['date'].dt.year.astype(int)
    df['month'] = df['date'].dt.month.astype(int)
    df['day']   = df['date'].dt.strftime('%Y-%m-%d')

    # ── 연도 선택
    cur_year = NOW_KST.year
    years = sorted(df['year'].unique().tolist())
    default_year = cur_year if cur_year in years else (years[-1] if years else cur_year)
    c1, c2 = st.columns([3,2])
    with c1:
        year = st.selectbox('연도(연간 리셋/독립 집계)', years, index=years.index(default_year), key='stat_year')
    with c2:
        st.caption('선택 연도 외 데이터는 저장만 유지(열람 전용)')

    dfY = df[df['year'] == year].copy()
    if dfY.empty:
        st.warning(f'{year}년 데이터가 없습니다.')
        st.stop()

    # ============================
    # 하위 탭: 팀원별 / 업체종합 / 업체개별
    # ============================
    tab_mem, tab_loc_all, tab_loc_each = st.tabs(['팀원별', '업체종합', '업체개별'])

    # ───────── 1) 팀원별 ─────────
    with tab_mem:
        st.markdown('#### 팀원별 수입 통계')

        members = sorted([m for m in dfY['member'].dropna().unique().tolist() if m])
        member_select = st.selectbox(
            '팀원 선택(최상단은 비교 보기)',
            ['팀원 비교(전체)'] + members,
            index=0,
            key='mem_select'
        )

        if member_select == '팀원 비교(전체)':
            # 연간 합계 (팀원별)
            annual_by_member = dfY.groupby('member', dropna=False, as_index=False)['amount'].sum()
            annual_by_member.rename(columns={'member':'팀원', 'amount':'연간 합계(만원)'}, inplace=True)
            annual_by_member.sort_values('연간 합계(만원)', ascending=False, inplace=True, kind='mergesort')
            annual_by_member['순위'] = range(1, len(annual_by_member)+1)
            annual_by_member = annual_by_member[['순위','팀원','연간 합계(만원)']]

            st.markdown('##### 연간 합계')
            st.dataframe(
                annual_by_member,
                use_container_width=True,
                hide_index=True,
                column_config={'연간 합계(만원)': st.column_config.NumberColumn(format='%.0f')}
            )

            # 월 선택 (보험/비보험 분리)
            months_avail_all = sorted(dfY['month'].unique().tolist())
            if months_avail_all:
                month_sel2 = st.selectbox('월 선택(보험/비보험 분리 보기)', months_avail_all, index=len(months_avail_all)-1, key='mem_month_all')
                df_month = dfY[dfY['month'] == month_sel2].copy()
                by_mem_cat = df_month.groupby(['member','category'], dropna=False)['amount'].sum().reset_index()
                pivot = by_mem_cat.pivot(index='member', columns='category', values='amount').fillna(0.0)
                for col in ['보험','비보험']:
                    if col not in pivot.columns: pivot[col] = 0.0
                pivot = pivot[['보험','비보험']]
                pivot['총합(만원)'] = pivot['보험'] + pivot['비보험']
                pivot = pivot.sort_values('총합(만원)', ascending=False).reset_index().rename(columns={'member':'팀원'})

                st.markdown(f'##### {month_sel2}월 · 보험/비보험 분리 + 총합')
                st.dataframe(
                    pivot[['팀원','총합(만원)','보험','비보험']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={c: st.column_config.NumberColumn(format='%.0f') for c in ['총합(만원)','보험','비보험']}
                )
            else:
                st.info('해당 연도의 월 데이터가 없습니다.')

        else:
            # 해당 팀원 데이터
            dfM_all = dfY[dfY['member'] == member_select].copy()
            months_avail = sorted(dfM_all['month'].unique().tolist()) or list(range(1, 13))
            month_sel = st.selectbox('월 선택(일별 상세/요약)', months_avail, index=(len(months_avail)-1 if months_avail else 0), key='mem_month_single')

            # 연간 요약
            y_ins_amt = dfM_all.loc[dfM_all['category']=='보험',   'amount'].sum()
            y_non_amt = dfM_all.loc[dfM_all['category']=='비보험', 'amount'].sum()
            y_tot_amt = dfM_all['amount'].sum()
            y_ins_cnt = int((dfM_all['category']=='보험').sum())
            y_non_cnt = int((dfM_all['category']=='비보험').sum())
            y_tot_cnt = int(len(dfM_all))

            st.markdown('##### 연간 요약')
            metric_cards([
                ("연간 총합(만원)", f"{y_tot_amt:,.0f}"),
                ("연간 보험(만원)", f"{y_ins_amt:,.0f}"),
                ("연간 비보험(만원)", f"{y_non_amt:,.0f}"),
                ("연간 건수(총합)", f"{y_tot_cnt:,}"),
                ("연간 건수(보험)", f"{y_ins_cnt:,}"),
                ("연간 건수(비보험)", f"{y_non_cnt:,}"),
            ])

            # 월간 요약
            dfM_month = dfM_all[dfM_all['month'] == month_sel].copy()
            m_ins_amt = dfM_month.loc[dfM_month['category']=='보험',   'amount'].sum()
            m_non_amt = dfM_month.loc[dfM_month['category']=='비보험', 'amount'].sum()
            m_tot_amt = dfM_month['amount'].sum()
            m_ins_cnt = int((dfM_month['category']=='보험').sum())
            m_non_cnt = int((dfM_month['category']=='비보험').sum())
            m_tot_cnt = int(len(dfM_month))

            st.markdown(f'##### {month_sel}월 요약')
            metric_cards([
                ("월 총합(만원)", f"{m_tot_amt:,.0f}"),
                ("월 보험(만원)", f"{m_ins_amt:,.0f}"),
                ("월 비보험(만원)", f"{m_non_amt:,.0f}"),
                ("월 건수(총합)", f"{m_tot_cnt:,}"),
                ("월 건수(보험)", f"{m_ins_cnt:,}"),
                ("월 건수(비보험)", f"{m_non_cnt:,}"),
            ])

            # 일별 합계
            daily = (
                dfM_all[dfM_all['month'] == month_sel]
                .groupby('day', dropna=False)['amount'].sum().reset_index()
                .rename(columns={'day':'날짜','amount':'금액(만원)'}).sort_values('날짜')
            )
            st.markdown(f'##### {member_select} · {month_sel}월 일별 합계')
            st.dataframe(
                daily,
                use_container_width=True,
                hide_index=True,
                column_config={'금액(만원)': st.column_config.NumberColumn(format='%.0f')}
            )

            # 상세 보기
            days_in_month = sorted(dfM_all.loc[dfM_all['month'] == month_sel, 'day'].dropna().unique().tolist())
            if days_in_month:
                sel_day = st.selectbox('상세 보기 날짜 선택', days_in_month, key='member_day_detail')
                details = dfM_all[(dfM_all['day'] == sel_day) & (dfM_all['month'] == month_sel)][
                    ['day','location','category','amount','memo']
                ].copy().rename(columns={'day':'날짜','location':'업체','category':'분류','amount':'금액(만원)','memo':'메모'})
                st.markdown(f'##### {member_select} · {sel_day} 입력 내역')
                st.dataframe(
                    details.sort_values(['업체','금액(만원)'], ascending=[True, False]),
                    use_container_width=True,
                    hide_index=True,
                    column_config={'금액(만원)': st.column_config.NumberColumn(format='%.0f')}
                )
            else:
                st.info('선택한 월에 입력된 데이터가 없어 상세 보기를 표시할 수 없습니다.')

    # ───────── 2) 업체종합 (요구: 랭킹 모드 순서 = 연간 → 월간) ─────────
    with tab_loc_all:
        st.markdown('#### 업체종합 (보험/비보험 분리)')
        cat_sel = st.radio('분류 선택', ['보험','비보험'], horizontal=True, key='loc_all_cat')
        dfC = dfY[dfY['category'] == cat_sel].copy()

        if dfC.empty:
            st.warning(f'{year}년 {cat_sel} 데이터가 없습니다.')
        else:
            rank_mode = st.radio('랭킹 모드', ['연간 순위','월간 순위'], horizontal=True, index=0, key='loc_all_mode')

            if rank_mode == '연간 순위':
                annual_loc = (
                    dfC.groupby('location', dropna=False)['amount'].sum().reset_index()
                    .rename(columns={'location':'업체','amount':'연간합계(만원)'})
                    .sort_values('연간합계(만원)', ascending=False).reset_index(drop=True)
                )
                annual_loc.insert(0, '순위', annual_loc.index + 1)
                st.markdown(f'##### {cat_sel} · 업체별 연간 순위')
                st.dataframe(
                    annual_loc[['순위','업체','연간합계(만원)']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={'연간합계(만원)': st.column_config.NumberColumn(format='%.0f')}
                )
            else:
                months_avail_c = sorted(dfC['month'].unique().tolist())
                if not months_avail_c:
                    st.info('선택 가능한 월이 없습니다.')
                else:
                    month_rank = st.selectbox('월 선택(해당 월만 표시)', months_avail_c, index=len(months_avail_c)-1, key='loc_all_month')
                    df_month = dfC[dfC['month'] == month_rank].copy()
                    monthly_loc = (
                        df_month.groupby('location', dropna=False)['amount'].sum().reset_index()
                        .rename(columns={'location':'업체','amount':'월합계(만원)'})
                        .sort_values('월합계(만원)', ascending=False).reset_index(drop=True)
                    )
                    monthly_loc.insert(0, '순위', monthly_loc.index + 1)
                    st.markdown(f'##### {cat_sel} · {month_rank}월 업체별 순위')
                    st.dataframe(
                        monthly_loc[['순위','업체','월합계(만원)']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={'월합계(만원)': st.column_config.NumberColumn(format='%.0f')}
                    )

    # ───────── 3) 업체개별 (요구: 단일 선택, 랭킹 모드 순서 = 월간 → 연간, 표로 표시, 우선순위 정렬) ─────────
    with tab_loc_each:
        st.markdown('#### 업체개별 (선택 업체 × 팀원별 결과)')

        # 1) 분류(보험/비보험)
        cat_sel_e = st.radio('분류 선택', ['보험', '비보험'], horizontal=True, key='loc_each_cat')
        dfC_e = dfY[dfY['category'] == cat_sel_e].copy()
        if dfC_e.empty:
            st.warning(f"{year}년 {cat_sel_e} 데이터가 없습니다.")
            st.stop()

        # 2) 기준: 월간 → 연간
        mode_e = st.radio('기준 선택', ['월간 순위', '연간 순위'], horizontal=True, index=0, key='loc_each_mode')

        # 3) 업체 단일 선택  ✅ 커스텀 정렬: [부산숨, 성모안과, 아ми유외과, 이진용외과] + 수입입력 탭 원본 순서
        priority = ["부산숨", "성모안과", "아미유외과", "이진용외과"]

        # 수입입력 탭(세션)의 locations 원본 순서
        base_order = [x.get('name') for x in st.session_state.locations if x.get('name')]

        # 현재 분류(cat_sel_e)에 실제 데이터가 존재하는 업체만
        present = set(dfC_e['location'].dropna().tolist())

        # 원본 순서에서 "현재 존재" 업체만
        ordered_filtered = [name for name in base_order if name in present]

        # 우선순위 4개를 맨 앞에, 나머지는 원본 순서(중복 제거)
        loc_opts_e = [n for n in priority if n in ordered_filtered] + [n for n in ordered_filtered if n not in priority]

        if not loc_opts_e:
            st.info('선택 가능한 업체가 없습니다.')
            st.stop()

        sel_loc_e = st.selectbox('업체 선택', loc_opts_e, index=0, key='loc_each_loc')

        # 선택된 업체 필터
        dfS_e = dfC_e[dfC_e['location'] == sel_loc_e].copy()

        # 표 유틸: 합계 행을 추가한 데이터프레임 반환
        def _df_with_total(df_in: pd.DataFrame, amount_col: str, name_col: str = '팀원') -> pd.DataFrame:
            total = pd.DataFrame([{name_col: '총합', amount_col: df_in[amount_col].sum()}])
            out = pd.concat([df_in, total], ignore_index=True)
            return out

        if mode_e == '월간 순위':
            months_avail_e = sorted(dfS_e['month'].dropna().unique().tolist())
            if not months_avail_e:
                st.info('선택된 업체에 해당하는 월 데이터가 없습니다.')
                st.stop()

            month_sel_e = st.selectbox('월 선택', months_avail_e, index=len(months_avail_e) - 1, key='loc_each_month')

            st.markdown(
                f"**선택된 업체:** {sel_loc_e}  \n"
                f"**조건:** {cat_sel_e} · {month_sel_e}월 기준"
            )

            # 팀원별 월간 합계
            dfM_e = dfS_e[dfS_e['month'] == month_sel_e].copy()
            by_member_month_e = (
                dfM_e.groupby('member', dropna=False)['amount'].sum().reset_index()
                .rename(columns={'member':'팀원','amount':'월합계(만원)'})
                .sort_values('월합계(만원)', ascending=False).reset_index(drop=True)
            )
            by_member_month_e = _df_with_total(by_member_month_e, '월합계(만원)')

            st.dataframe(
                by_member_month_e,
                use_container_width=True,
                hide_index=True,
                column_config={'월합계(만원)': st.column_config.NumberColumn(format='%.0f')}
            )

            # 아래에 참고: 연간 합계 표
            st.markdown('##### 참고: 팀원별 연간 합계')
            by_member_year_e = (
                dfS_e.groupby('member', dropna=False)['amount'].sum().reset_index()
                .rename(columns={'member':'팀원','amount':'연간합계(만원)'})
                .sort_values('연간합계(만원)', ascending=False).reset_index(drop=True)
            )
            by_member_year_e = _df_with_total(by_member_year_e, '연간합계(만원)')
            st.dataframe(
                by_member_year_e,
                use_container_width=True,
                hide_index=True,
                column_config={'연간합계(만원)': st.column_config.NumberColumn(format='%.0f')}
            )

        else:  # 연간 순위
            st.markdown(
                f"**선택된 업체:** {sel_loc_e}  \n"
                f"**조건:** {cat_sel_e} · 연간 기준"
            )

            by_member_year_e = (
                dfS_e.groupby('member', dropna=False)['amount'].sum().reset_index()
                .rename(columns={'member':'팀원','amount':'연간합계(만원)'})
                .sort_values('연간합계(만원)', ascending=False).reset_index(drop=True)
            )
            by_member_year_e = _df_with_total(by_member_year_e, '연간합계(만원)')
            st.dataframe(
                by_member_year_e,
                use_container_width=True,
                hide_index=True,
                column_config={'연간합계(만원)': st.column_config.NumberColumn(format='%.0f')}
            )


# ============================
# Tab 3: 설정 (팀원/업체 추가·삭제·순서 이동)
# ============================
with tab3:
    st.subheader("설정")
    st.caption("📱 모바일에서는 화면을 가로로 돌리면 설정 UI가 더 깔끔하게 표시됩니다.")
    def open_confirm(_type, _id, _name, action):
        st.session_state["confirm_target"] = {"type": _type, "id": _id, "name": _name}
        st.session_state["confirm_action"] = action

    def close_confirm():
        st.session_state["confirm_target"] = None
        st.session_state["confirm_action"] = None

    if st.session_state.get("confirm_target"):
        tgt = st.session_state["confirm_target"]; action = st.session_state.get("confirm_action")
        with st.container(border=True):
            st.warning(f"정말로 **{tgt['name']}** 을(를) **{'삭제' if action=='delete' else action}** 하시겠습니까?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ 확인"):
                    if action == "delete":
                        if tgt["type"] == "member": delete_row("team_members", tgt["id"])
                        elif tgt["type"] == "location": delete_row("locations", tgt["id"])
                    close_confirm(); st.rerun()
            with cc2:
                if st.button("❌ 취소"): close_confirm(); st.rerun()

    # ───────── 팀원 관리 ─────────
    st.markdown("### 👤 팀원 관리")
    with st.form("add_member_form", clear_on_submit=True):
        new_member = st.text_input("이름", "")
        submitted = st.form_submit_button("팀원 추가")
        if submitted:
            if new_member.strip():
                mid = f"m_{datetime.utcnow().timestamp()}"
                next_order = (max([x.get("order", 0) for x in st.session_state.team_members] or [-1]) + 1)
                upsert_row("team_members", {"id": mid, "name": new_member.strip(), "order": next_order})
                st.success("팀원 추가 완료"); st.rerun()
            else:
                st.error("이름을 입력하세요.")

    if st.session_state.team_members:
        st.markdown("#### 팀원 목록 (순서 이동/삭제)")
        tm = sorted(st.session_state.team_members, key=lambda x: x.get("order", 0))

        st.markdown('<div class="manage-inline">', unsafe_allow_html=True)
        mh1, mh2, mh3, mh4 = st.columns([6, 1, 1, 1])
        with mh1: st.markdown('<div class="hdr">이름</div>', unsafe_allow_html=True)
        with mh2: st.markdown('<div class="hdr">위로</div>', unsafe_allow_html=True)
        with mh3: st.markdown('<div class="hdr">아래로</div>', unsafe_allow_html=True)
        with mh4: st.markdown('<div class="hdr">삭제</div>', unsafe_allow_html=True)

        for i, m in enumerate(tm):
            c1, c2, c3, c4 = st.columns([6, 1, 1, 1])
            with c1: st.markdown(f'<div class="row name-col">**{m["name"]}**</div>', unsafe_allow_html=True)
            with c2:
                if st.button("▲", key=f"member_up_{m['id']}", disabled=(i == 0)):
                    swap_order("team_members", i, i-1)
            with c3:
                if st.button("▼", key=f"member_down_{m['id']}", disabled=(i == len(tm)-1)):
                    swap_order("team_members", i, i+1)
            with c4:
                if st.button("🗑️", key=f"member_del_{m['id']}"):
                    open_confirm("member", m["id"], m["name"], "delete"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("등록된 팀원이 없습니다.")

    st.divider()

    # ───────── 업체 관리 ─────────
    st.markdown("### 🏢 업체 관리")
    with st.form("add_location_form", clear_on_submit=True):
        loc_name = st.text_input("업체명", "")
        loc_cat  = st.selectbox("분류", ["보험", "비보험"])
        submitted = st.form_submit_button("업체 추가")
        if submitted:
            if loc_name.strip():
                lid = f"l_{datetime.utcnow().timestamp()}"
                next_order = (max([x.get("order", 0) for x in st.session_state.locations] or [-1]) + 1)
                upsert_row("locations", {"id": lid, "name": loc_name.strip(), "category": loc_cat.strip(), "order": next_order})
                st.success("업체 추가 완료"); st.rerun()
            else:
                st.error("업체명을 입력하세요.")

    if st.session_state.locations:
        st.markdown("#### 업체 목록 (카테고리별 순서 이동/삭제)")
        locs_all = sorted(st.session_state.locations, key=lambda x: x.get("order", 0))
        for l in locs_all:
            if isinstance(l.get("category"), str): l["category"] = l["category"].strip()

        cat_view = st.radio("보기(카테고리)", ["보험", "비보험"], horizontal=True, key="loc_cat_view")
        filtered = [(i, l) for i, l in enumerate(locs_all) if l.get("category") == cat_view]

        st.markdown('<div class="manage-inline">', unsafe_allow_html=True)
        h1, h2, h3, h4, h5 = st.columns([5.5, 2, 1, 1, 1])
        with h1: st.markdown('<div class="hdr">업체명</div>', unsafe_allow_html=True)
        with h2: st.markdown('<div class="hdr">분류</div>', unsafe_allow_html=True)
        with h3: st.markdown('<div class="hdr">위로</div>', unsafe_allow_html=True)
        with h4: st.markdown('<div class="hdr">아래로</div>', unsafe_allow_html=True)
        with h5: st.markdown('<div class="hdr">삭제</div>', unsafe_allow_html=True)

        def move_in_category(k_from: int, k_to: int):
            i_master_from = filtered[k_from][0]
            i_master_to   = filtered[k_to][0]
            swap_order("locations", i_master_from, i_master_to)

        if not filtered:
            st.info(f"'{cat_view}' 분류에 등록된 업체가 없습니다.")
        else:
            for k, (i_master, l) in enumerate(filtered):
                c1, c2, c3, c4, c5 = st.columns([5.5, 2, 1, 1, 1])
                with c1: st.markdown(f'<div class="row name-col">**{l["name"]}**</div>', unsafe_allow_html=True)
                with c2: st.write(l.get("category", ""))
                with c3:
                    if st.button("▲", key=f"loc_up_{l['id']}", disabled=(k == 0)):
                        move_in_category(k, k-1)
                with c4:
                    if st.button("▼", key=f"loc_down_{l['id']}", disabled=(k == len(filtered)-1)):
                        move_in_category(k, k+1)
                with c5:
                    if st.button("🗑️", key=f"loc_del_{l['id']}"):
                        open_confirm("location", l["id"], l["name"], "delete"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("등록된 업체가 없습니다.")

    st.divider()
    if st.button("데이터 새로고침"):
        load_data(); st.success("새로고침 완료"); st.rerun()

# ============================
# Tab 4: 기록 관리 (전체 수정/삭제)
# ============================
with tab4:
    st.subheader("기록 관리 (전체 수정/삭제)")

    def resolve_name2(id_value: str, coll: list[dict]) -> str:
        for x in coll:
            if x["id"] == id_value: return x.get("name", "")
        return ""

    records = st.session_state.get("income_records", [])
    if not records:
        st.info("데이터가 없습니다. 먼저 [수입 입력]에서 데이터를 추가해 주세요.")
        st.stop()

    df = pd.DataFrame([{
        "id": r.get("id"),
        "date": r.get("date"),
        "amount": pd.to_numeric(r.get("amount"), errors="coerce"),
        "member_id": r.get("teamMemberId"),
        "member": resolve_name2(r.get("teamMemberId",""), st.session_state.team_members),
        "location_id": r.get("locationId"),
        "location": resolve_name2(r.get("locationId",""), st.session_state.locations),
        "category": next((l["category"] for l in st.session_state.locations if l["id"] == r.get("locationId")), ""),
        "memo": r.get("memo",""),
    } for r in records])
    df["amount"] = df["amount"].fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["year"] = df["date"].dt.year
    df["day"] = df["date"].dt.strftime("%Y-%m-%d")

    years = sorted(df["year"].unique().tolist())
    c1, c2, c3 = st.columns([2,3,2])
    with c1: year_sel = st.selectbox("연도", years, index=len(years)-1)
    dmin = df.loc[df["year"]==year_sel, "date"].min().date()
    dmax = df.loc[df["year"]==year_sel, "date"].max().date()
    with c2: date_range = st.date_input("기간", value=(dmin, dmax), min_value=dmin, max_value=dmax, format="YYYY-MM-DD")
    with c3: order_by = st.selectbox("정렬", ["날짜↓(최신)", "날짜↑", "금액↓", "금액↑"])

    c4, c5, c6 = st.columns([2,2,2])
    with c4:
        mem_opts = ["전체"] + sorted([m["name"] for m in st.session_state.team_members])
        mem_sel = st.selectbox("팀원", mem_opts, index=0)
    with c5:
        cat_sel = st.selectbox("분류", ["전체","보험","비보험"], index=0)
    with c6:
        loc_candidates = [l for l in st.session_state.locations if (cat_sel=="전체" or l["category"]==cat_sel)]
        loc_opts = ["전체"] + [l["name"] for l in sorted(loc_candidates, key=lambda x: x.get("order",0))]
        loc_sel = st.selectbox("업체", loc_opts, index=0)

    q = df[df["year"]==year_sel].copy()
    if isinstance(date_range, tuple) and len(date_range)==2:
        q = q[(q["date"].dt.date >= date_range[0]) & (q["date"].dt.date <= date_range[1])]
    if mem_sel != "전체": q = q[q["member"] == mem_sel]
    if cat_sel != "전체": q = q[q["category"] == cat_sel]
    if loc_sel != "전체": q = q[q["location"] == loc_sel]

    if order_by == "날짜↓(최신)":
        q = q.sort_values(["date","id"], ascending=[False, True])
    elif order_by == "날짜↑":
        q = q.sort_values(["date","id"], ascending=[True, True])
    elif order_by == "금액↓":
        q = q.sort_values(["amount","date"], ascending=[False, False])
    else:
        q = q.sort_values(["amount","date"], ascending=[True, False])

    PAGE_SIZE = 20
    total = len(q); total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
    st.session_state.records_page = min(st.session_state.records_page, total_pages-1)
    st.session_state.records_page = max(st.session_state.records_page, 0)

    pc1, pc2, pc3 = st.columns([1,2,1])
    with pc1:
        if st.button("⬅ 이전", disabled=(st.session_state.records_page==0)):
            st.session_state.records_page -= 1; st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center'>페이지 {st.session_state.records_page+1} / {total_pages} (총 {total}건)</div>", unsafe_allow_html=True)
    with pc3:
        if st.button("다음 ➡", disabled=(st.session_state.records_page>=total_pages-1)):
            st.session_state.records_page += 1; st.rerun()

    start = st.session_state.records_page * PAGE_SIZE
    page_df = q.iloc[start:start+PAGE_SIZE].copy()

    csv_bytes = page_df[["day","member","location","category","amount","memo"]].rename(
        columns={"day":"날짜","member":"팀원","location":"업체","category":"분류","amount":"금액(만원)","memo":"메모"}
    ).to_csv(index=False).encode("utf-8-sig")
    st.download_button("현재 페이지 CSV 다운로드", data=csv_bytes, file_name=f"records_{year_sel}_{st.session_state.records_page+1}.csv", mime="text/csv")

    st.markdown("#### 결과 (선택/수정/삭제)")
    st.dataframe(
        page_df[["day","member","location","category","amount","memo"]].rename(
            columns={"day":"날짜","member":"팀원","location":"업체","category":"분류","amount":"금액(만원)","memo":"메모"}
        ),
        use_container_width=True,
        column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")}
    )

    for _, row in page_df.iterrows():
        with st.container(border=True):
            left, right = st.columns([6, 2])
            left.write(f"**{row['day']} · {row['member']} · {row['location']} · {int(row['amount']):,}만원** — {row['memo']}")
            with right:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🖉 수정", key=f"edit_any_{row['id']}"):
                        st.session_state.edit_income_id = row["id"]; st.rerun()
                with col_b:
                    if st.button("🗑 삭제", key=f"del_any_{row['id']}"):
                        st.session_state.confirm_delete_income_id = row["id"]; st.rerun()

    if st.session_state.confirm_delete_income_id:
        rid = st.session_state.confirm_delete_income_id
        with st.container(border=True):
            st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 삭제 확정"):
                    delete_row("incomes", rid)
                    st.session_state.confirm_delete_income_id = None
                    st.success("삭제되었습니다."); st.rerun()
            with c2:
                if st.button("❌ 취소"):
                    st.session_state.confirm_delete_income_id = None; st.rerun()

    if st.session_state.edit_income_id:
        target = next((x for x in st.session_state.income_records if x["id"] == st.session_state.edit_income_id), None)
        if target:
            st.markdown("#### 선택한 기록 수정")
            def resolve_name(id_value: str, coll: list[dict]) -> str:
                for x in coll:
                    if x["id"] == id_value: return x.get("name", "")
                return ""
            cur_member = resolve_name(target["teamMemberId"], st.session_state.team_members)
            cur_loc = next((l for l in st.session_state.locations if l["id"] == target["locationId"]), None)
            cur_cat = cur_loc["category"] if cur_loc else "보험"

            c1, c2 = st.columns([1,1])
            with c1:
                new_date = st.date_input("발생일", value=pd.to_datetime(target["date"]).date(), format="YYYY-MM-DD", key="edit_any_date")
                member_options = {m["name"]: m["id"] for m in st.session_state.team_members}
                member_name_edit = st.selectbox("팀원", list(member_options.keys()),
                                                index=list(member_options.keys()).index(cur_member), key="edit_any_member")
                member_id_edit = member_options[member_name_edit]
            with c2:
                cat_edit = st.radio("분류", ["보험","비보험"], index=0 if cur_cat=="보험" else 1, horizontal=True, key="edit_any_cat")
                filtered_locations = [l for l in st.session_state.locations if l["category"] == cat_edit]
                loc_options = {l["name"]: l["id"] for l in filtered_locations}
                default_loc_idx = 0
                if cur_loc and cur_loc["category"] == cat_edit:
                    names = list(loc_options.keys())
                    if cur_loc["name"] in names: default_loc_idx = names.index(cur_loc["name"])
                loc_name_edit = st.selectbox("업체", list(loc_options.keys()), index=default_loc_idx, key="edit_any_loc")
                loc_id_edit = loc_options[loc_name_edit]

            amount_raw_edit = st.text_input("금액(만원 단위)", value=str(int(float(target["amount"]))), placeholder="예: 50 (만원)", key="edit_any_amount")
            try:
                amount_edit = float(amount_raw_edit.replace(",", "").strip())
            except ValueError:
                amount_edit = None; st.error("금액은 숫자만 입력하세요. (예: 50)")
            memo_edit = st.text_input("메모(선택)", value=target.get("memo",""), key="edit_any_memo")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅ 저장", type="primary", key="edit_any_save"):
                    if amount_edit is None or amount_edit <= 0:
                        st.error("금액을 올바르게 입력하세요.")
                    else:
                        update_income(target["id"], {
                            "date": new_date.strftime("%Y-%m-%d"),
                            "teamMemberId": member_id_edit,
                            "locationId": loc_id_edit,
                            "amount": float(amount_edit),
                            "memo": memo_edit,
                        })
                        st.session_state.edit_income_id = None
                        st.success("수정되었습니다."); st.rerun()
            with b2:
                if st.button("❌ 취소", key="edit_any_cancel"):
                    st.session_state.edit_income_id = None; st.rerun()



# ============================
# Tab 5: 정산 (Supabase 연동, 안전 쿼리)
# - 빈 결과에서도 오류 없이 동작 (maybe_single / limit(1))
# - 수입 없어도 팀비/이체만으로 정산 표시
# - 금액 입력칸은 빈칸(정수)
# - 팀비/이체 내역: 표 + 수정/삭제(확인)
# - 웨일 브라우저 expander 보정 CSS
# ============================
with tab5:
    st.markdown("### 정산")

    # ─────────────────────────────
    # 웨일 렌더링 보정 CSS
    # ─────────────────────────────
    st.markdown("""
    <style>
    details > summary { line-height: 1.5 !important; white-space: normal !important; }
    .streamlit-expanderHeader p { line-height: 1.5 !important; white-space: normal !important; word-break: keep-all; overflow-wrap: anywhere; }
    .streamlit-expanderHeader svg { transform: translateY(1px); }
    </style>
    """, unsafe_allow_html=True)

    # ─────────────────────────────
    # Helpers
    # ─────────────────────────────
    def _name_from(_id: str, coll: list[dict]) -> str:
        for x in coll:
            if x.get("id") == _id:
                return x.get("name", "")
        return ""

    def _member_names() -> list[str]:
        return [x.get("name") for x in st.session_state.team_members if x.get("name")]

    def _group_by_member(df_in: pd.DataFrame) -> pd.DataFrame:
        if df_in.empty:
            return pd.DataFrame(columns=["member","amount"])
        return df_in.groupby("member", dropna=False)["amount"].sum().reset_index()

    # ── Supabase 핸들 (상단의 get_supabase_client()로 생성된 sb 사용)
    #    필요 시 st.session_state.supabase 로도 받아봄
    sb = sb or st.session_state.get("supabase")

    # ── Supabase CRUD (빈 결과 안전)
    def sb_get_month(ym_key: str):
        if not sb:
            return None
        try:
            qb = sb.table("settlement_month").select("*").eq("ym_key", ym_key)
            # 라이브러리 버전에 따라 maybe_single이 없을 수 있음
            try:
                res = qb.maybe_single().execute()   # 0행: data=None, 1행: dict
                return getattr(res, "data", None)
            except AttributeError:
                res = qb.limit(1).execute()         # 대체 전략
                data = getattr(res, "data", None) or []
                return data[0] if data else None
        except Exception as e:
            st.warning(f"월 설정 조회 실패: {e}")
            return None

    def sb_upsert_month(ym_key: str, sungmo_fixed: int, recv_bs: str, recv_am: str):
        if not sb:
            return
        from datetime import datetime, timezone
        payload = {
            "ym_key": ym_key,
            "sungmo_fixed": int(sungmo_fixed),
            "receiver_busansoom": recv_bs,
            "receiver_amiyou": recv_am,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        sb.table("settlement_month").upsert(payload, on_conflict="ym_key").execute()

    def sb_list_teamfee(ym_key: str):
        if not sb:
            return []
        res = (sb.table("settlement_teamfee").select("*")
               .eq("ym_key", ym_key).order("created_at", desc=False).execute())
        return getattr(res, "data", None) or []

    def sb_add_teamfee(ym_key: str, who: str, amount: int, memo: str):
        if not sb:
            return
        sb.table("settlement_teamfee").insert({
            "ym_key": ym_key, "who": who, "amount": int(amount), "memo": memo
        }).execute()

    def sb_update_teamfee(item_id: int, who: str, amount: int, memo: str):
        if not sb:
            return
        sb.table("settlement_teamfee").update({
            "who": who, "amount": int(amount), "memo": memo
        }).eq("id", item_id).execute()

    def sb_delete_teamfee(item_id: int):
        if not sb:
            return
        sb.table("settlement_teamfee").delete().eq("id", item_id).execute()

    def sb_list_transfer(ym_key: str):
        if not sb:
            return []
        res = (sb.table("settlement_transfer").select("*")
               .eq("ym_key", ym_key).order("created_at", desc=False).execute())
        return getattr(res, "data", None) or []

    def sb_add_transfer(ym_key: str, from_name: str, to_name: str, amount: int, memo: str):
        if not sb:
            return
        sb.table("settlement_transfer").insert({
            "ym_key": ym_key, "from": from_name, "to": to_name,
            "amount": int(amount), "memo": memo
        }).execute()

    def sb_update_transfer(item_id: int, from_name: str, to_name: str, amount: int, memo: str):
        if not sb:
            return
        sb.table("settlement_transfer").update({
            "from": from_name, "to": to_name, "amount": int(amount), "memo": memo
        }).eq("id", item_id).execute()

    def sb_delete_transfer(item_id: int):
        if not sb:
            return
        sb.table("settlement_transfer").delete().eq("id", item_id).execute()

    # ─────────────────────────────
    # 원천 수입 데이터 → DF
    # ─────────────────────────────
    records = st.session_state.get("income_records", [])
    if not records:
        st.info("수입 데이터가 없습니다. 먼저 [수입 입력]에서 데이터를 추가해 주세요.")
        st.stop()

    df = pd.DataFrame([{
        "date": r.get("date"),
        "amount": pd.to_numeric(r.get("amount"), errors="coerce"),
        "member": _name_from(r.get("teamMemberId",""), st.session_state.team_members),
        "location": _name_from(r.get("locationId",""), st.session_state.locations),
        "category": next((l.get("category") for l in st.session_state.locations if l.get("id")==r.get("locationId")), ""),
        "memo": r.get("memo",""),
    } for r in records])
    df["amount"] = df["amount"].fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["year"]  = df["date"].dt.year.astype(int)
    df["month"] = df["date"].dt.month.astype(int)
    df["day"]   = df["date"].dt.strftime("%Y-%m-%d")

    members_all = _member_names()

    # ─────────────────────────────
    # 연/월 선택
    # ─────────────────────────────
    years = sorted(df["year"].unique().tolist())
    cur_year = NOW_KST.year
    default_year = cur_year if cur_year in years else (years[-1] if years else cur_year)

    c1, c2, _ = st.columns([1,1,2])
    with c1:
        year = st.selectbox("정산 연도", years, index=years.index(default_year), key="settle5_year")
    months = sorted(df[df["year"]==year]["month"].unique().tolist())
    with c2:
        month = st.selectbox("정산 월", months, index=len(months)-1, key="settle5_month")
    ym_key = f"{year:04d}-{month:02d}"

    # ─────────────────────────────
    # 월 설정 로드/생성 (빈 결과 안전)
    # ─────────────────────────────
    if not sb:
        st.warning("Supabase가 설정되지 않았습니다. 정산 입력 저장/공유를 하려면 secrets에 SUPABASE 설정이 필요합니다.")
        month_row = {
            "ym_key": ym_key, "sungmo_fixed": 650,
            "receiver_busansoom": (members_all[0] if members_all else ""),
            "receiver_amiyou":    (members_all[0] if members_all else ""),
        }
    else:
        month_row = sb_get_month(ym_key)
        if not month_row:
            default_bs = members_all[0] if members_all else ""
            default_am = members_all[0] if members_all else ""
            try:
                sb_upsert_month(ym_key, 650, default_bs, default_am)
            except Exception as e:
                st.error(f"월 설정 생성 실패: {e}")
            month_row = sb_get_month(ym_key) or {
                "ym_key": ym_key, "sungmo_fixed": 650,
                "receiver_busansoom": default_bs, "receiver_amiyou": default_am
            }

    sungmo_fixed = int(month_row["sungmo_fixed"])
    recv_bs      = month_row["receiver_busansoom"]
    recv_am      = month_row["receiver_amiyou"]
    recv_lee     = "강현석"  # 고정

    # ─────────────────────────────
    # 서브탭: 입력 / 정산
    # ─────────────────────────────
    tab_input, tab_result = st.tabs(["입력", "정산"])

    # ============================
    # 입력 탭
    # ============================
    with tab_input:
        st.markdown("#### 월별 입력")

        # ───────── 기본 설정 ─────────
        with st.expander("기본 설정", expanded=True):
            colA, colB, colC = st.columns(3)
            with colA:
                new_fixed = st.number_input("성모 고정액(만원)", min_value=0, step=10,
                                            value=int(sungmo_fixed), format="%d", key=f"s5_sungmo_fixed_{ym_key}")
                if sb and new_fixed != sungmo_fixed:
                    sb_upsert_month(ym_key, int(new_fixed), recv_bs, recv_am); st.rerun()
            with colB:
                bs_idx = (members_all.index(recv_bs) if recv_bs in members_all else 0) if members_all else 0
                new_bs = st.selectbox("부산숨 수령자", members_all, index=bs_idx, key=f"s5_recv_bs_{ym_key}")
                if sb and new_bs != recv_bs:
                    sb_upsert_month(ym_key, int(new_fixed), new_bs, recv_am); st.rerun()
            with colC:
                am_idx = (members_all.index(recv_am) if recv_am in members_all else 0) if members_all else 0
                new_am = st.selectbox("아미유 수령자", members_all, index=am_idx, key=f"s5_recv_am_{ym_key}")
                if sb and new_am != recv_am:
                    sb_upsert_month(ym_key, int(new_fixed), new_bs, new_am); st.rerun()
            st.caption("이진용외과 수령자: **강현석(고정)**")

        # ───────── 팀비 사용 입력 ─────────
        with st.expander("팀비 사용 입력", expanded=True):
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                tf_who = st.selectbox("사용자", members_all, key=f"s5_tf_who_{ym_key}")
            with col2:
                tf_amt_str = st.text_input("금액(만원)", value="", key=f"s5_tf_amt_{ym_key}")
            with col3:
                tf_memo = st.text_input("메모", value="", key=f"s5_tf_memo_{ym_key}")
            if st.button("추가", type="primary", key=f"s5_btn_add_tf_{ym_key}"):
                try:
                    amt = int(tf_amt_str.strip())
                    if sb:
                        sb_add_teamfee(ym_key, tf_who, amt, tf_memo)
                        st.success("팀비 사용 항목이 추가되었습니다."); st.rerun()
                    else:
                        st.error("Supabase 미연결: 저장 불가")
                except ValueError:
                    st.error("금액을 숫자로 입력하세요.")

        # ───────── 팀비 사용 내역 (표 + 수정/삭제 확인) ─────────
        st.session_state.setdefault("confirm_tf_id", None)
        st.session_state.setdefault("confirm_tf_open", False)
        teamfee_items = sb_list_teamfee(ym_key) if sb else []
        if teamfee_items:
            st.markdown("##### 팀비 사용 내역")
            for row in teamfee_items:
                c1, c2, c3, c4, c5 = st.columns([1,1,2,1,1])
                c1.write(row["who"])
                c2.write(f"{row['amount']}만원")
                c3.write(row.get("memo",""))
                edit_clicked = c4.button("수정", key=f"tf_edit_{row['id']}_{ym_key}")
                del_clicked  = c5.button("삭제", key=f"tf_del_{row['id']}_{ym_key}")

                if del_clicked and sb:
                    st.session_state.confirm_tf_id = row["id"]
                    st.session_state.confirm_tf_open = True
                    st.rerun()

                if edit_clicked:
                    e1, e2, e3, e4, e5 = st.columns([1,1,2,1,1])
                    new_who  = e1.selectbox("사용자", members_all,
                                            index=(members_all.index(row["who"]) if row["who"] in members_all else 0),
                                            key=f"tf_edit_who_{row['id']}_{ym_key}")
                    new_amt  = e2.text_input("금액(만원)", value=str(row["amount"]), key=f"tf_edit_amt_{row['id']}_{ym_key}")
                    new_memo = e3.text_input("메모", value=row.get("memo",""), key=f"tf_edit_memo_{row['id']}_{ym_key}")
                    save_btn = e4.button("저장", key=f"tf_save_{row['id']}_{ym_key}")
                    cancel   = e5.button("취소", key=f"tf_cancel_{row['id']}_{ym_key}")
                    if save_btn and sb:
                        try:
                            sb_update_teamfee(row["id"], new_who, int(new_amt.strip()), new_memo)
                            st.success("저장되었습니다."); st.rerun()
                        except ValueError:
                            st.error("금액을 숫자로 입력하세요.")

            # 삭제 확인 모달 대체
            if st.session_state.get("confirm_tf_open", False) and st.session_state.get("confirm_tf_id") is not None:
                with st.container(border=True):
                    st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 삭제 확정", key="tf_confirm_yes"):
                            sb_delete_teamfee(st.session_state.confirm_tf_id)
                            st.session_state.confirm_tf_id = None
                            st.session_state.confirm_tf_open = False
                            st.success("삭제되었습니다."); st.rerun()
                    with c2:
                        if st.button("❌ 취소", key="tf_confirm_no"):
                            st.session_state.confirm_tf_id = None
                            st.session_state.confirm_tf_open = False
                            st.rerun()
        else:
            st.info("등록된 팀비 사용 항목이 없습니다.")

        # ───────── 팀원 간 이체 입력 ─────────
        with st.expander("팀원 간 이체 입력", expanded=True):
            col1, col2, col3, col4 = st.columns([1,1,1,2])
            with col1:
                tr_from = st.selectbox("보낸 사람", members_all, key=f"s5_tr_from_{ym_key}")
            with col2:
                tr_to = st.selectbox("받는 사람", [m for m in members_all if m != st.session_state.get(f"s5_tr_from_{ym_key}")], key=f"s5_tr_to_{ym_key}")
            with col3:
                tr_amt_str = st.text_input("금액(만원)", value="", key=f"s5_tr_amt_{ym_key}")
            with col4:
                tr_memo = st.text_input("메모", value="", key=f"s5_tr_memo_{ym_key}")
            if st.button("추가", type="primary", key=f"s5_btn_add_tr_{ym_key}"):
                try:
                    amt = int(tr_amt_str.strip())
                    if sb:
                        sb_add_transfer(ym_key, tr_from, tr_to, amt, tr_memo)
                        st.success("이체 항목이 추가되었습니다."); st.rerun()
                    else:
                        st.error("Supabase 미연결: 저장 불가")
                except ValueError:
                    st.error("금액을 숫자로 입력하세요.")

        # ───────── 이체 내역 (표 + 수정/삭제 확인) ─────────
        st.session_state.setdefault("confirm_tr_id", None)
        st.session_state.setdefault("confirm_tr_open", False)
        transfers = sb_list_transfer(ym_key) if sb else []
        if transfers:
            st.markdown("##### 팀원 간 이체 내역")
            for row in transfers:
                c1, c2, c3, c4, c5, c6, c7 = st.columns([1,0.3,1,2,1,1,1])
                c1.write(row["from"]); c2.write("→"); c3.write(row["to"])
                c4.write(row.get("memo","")); c5.write(f"{row['amount']}만원")
                edit_clicked = c6.button("수정", key=f"tr_edit_{row['id']}_{ym_key}")
                del_clicked  = c7.button("삭제", key=f"tr_del_{row['id']}_{ym_key}")

                if del_clicked and sb:
                    st.session_state.confirm_tr_id = row["id"]
                    st.session_state.confirm_tr_open = True
                    st.rerun()

                if edit_clicked:
                    e1, e2, e3, e4, e5, e6 = st.columns([1,1,1,2,1,1])
                    new_from = e1.selectbox("보낸 사람", members_all,
                                            index=(members_all.index(row["from"]) if row["from"] in members_all else 0),
                                            key=f"tr_edit_from_{row['id']}_{ym_key}")
                    recv_candidates = [m for m in members_all if m != new_from]
                    to_idx = recv_candidates.index(row["to"]) if row["to"] in recv_candidates else 0
                    new_to   = e2.selectbox("받는 사람", recv_candidates, index=to_idx, key=f"tr_edit_to_{row['id']}_{ym_key}")
                    new_amt  = e3.text_input("금액(만원)", value=str(row["amount"]), key=f"tr_edit_amt_{row['id']}_{ym_key}")
                    new_memo = e4.text_input("메모", value=row.get("memo",""), key=f"tr_edit_memo_{row['id']}_{ym_key}")
                    save_btn = e5.button("저장", key=f"tr_save_{row['id']}_{ym_key}")
                    cancel   = e6.button("취소", key=f"tr_cancel_{row['id']}_{ym_key}")
                    if save_btn and sb:
                        try:
                            sb_update_transfer(row["id"], new_from, new_to, int(new_amt.strip()), new_memo)
                            st.success("저장되었습니다."); st.rerun()
                        except ValueError:
                            st.error("금액을 숫자로 입력하세요.")

            # 삭제 확인
            if st.session_state.get("confirm_tr_open", False) and st.session_state.get("confirm_tr_id") is not None:
                with st.container(border=True):
                    st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 삭제 확정", key="tr_confirm_yes"):
                            sb_delete_transfer(st.session_state.confirm_tr_id)
                            st.session_state.confirm_tr_id = None
                            st.session_state.confirm_tr_open = False
                            st.success("삭제되었습니다."); st.rerun()
                    with c2:
                        if st.button("❌ 취소", key="tr_confirm_no"):
                            st.session_state.confirm_tr_id = None
                            st.session_state.confirm_tr_open = False
                            st.rerun()
        else:
            st.info("등록된 이체 항목이 없습니다.")

    # ============================
    # 정산 탭
    # ============================
    with tab_result:
        st.markdown("#### 정산 결과")

        dfM = df[(df["year"]==year) & (df["month"]==month)].copy()

        def income_by_loc(loc_name: str) -> pd.DataFrame:
            sub = dfM[dfM["location"] == loc_name]
            return _group_by_member(sub)

        # 명칭 추론(없으면 기본)
        bs_name  = next((n for n in dfM["location"].unique().tolist() if isinstance(n,str) and '숨' in n), "부산숨")
        sm_name  = next((n for n in dfM["location"].unique().tolist() if isinstance(n,str) and '성모' in n), "성모안과")
        amy_name = next((n for n in dfM["location"].unique().tolist() if isinstance(n,str) and '아미유' in n), "아미유외과")
        lee_name = next((n for n in dfM["location"].unique().tolist() if isinstance(n,str) and '이진용' in n), "이진용외과")

        income_bs  = income_by_loc(bs_name)
        income_sm  = income_by_loc(sm_name)
        income_amy = income_by_loc(amy_name)
        income_lee = income_by_loc(lee_name)

        # 최신 월 설정/입력 다시 로드
        if sb:
            month_row = sb_get_month(ym_key) or month_row
            teamfee_items = sb_list_teamfee(ym_key)
            transfers     = sb_list_transfer(ym_key)
        else:
            teamfee_items, transfers = [], []

        sungmo_fixed = int(month_row["sungmo_fixed"])
        recv_bs      = month_row["receiver_busansoom"]
        recv_am      = month_row["receiver_amiyou"]
        recv_lee     = "강현석"

        # 거래 생성 (수입 없어도 팀비/이체만으로 가능)
        tx = []

        # 부산숨 지급
        if recv_bs and not income_bs.empty:
            for _, r in income_bs.iterrows():
                m, amt = r["member"], float(r["amount"])
                if not m or m == recv_bs or amt <= 0: continue
                tx.append({"from": recv_bs, "to": m, "amount": int(round(amt)), "reason": bs_name})

        # 성모 (개인 실수입)
        if recv_bs and not income_sm.empty:
            for _, r in income_sm.iterrows():
                m, amt = r["member"], float(r["amount"])
                if not m or m == recv_bs or amt <= 0: continue
                tx.append({"from": recv_bs, "to": m, "amount": int(round(amt)), "reason": sm_name})

        # 이진용(강현석 → 팀원)
        if not income_lee.empty:
            for _, r in income_lee.iterrows():
                m, amt = r["member"], float(r["amount"])
                if not m or m == recv_lee or amt <= 0: continue
                tx.append({"from": recv_lee, "to": m, "amount": int(round(amt)), "reason": lee_name})

        # 아미유(recv_am → 팀원)
        if recv_am and not income_amy.empty:
            for _, r in income_amy.iterrows():
                m, amt = r["member"], float(r["amount"])
                if not m or m == recv_am or amt <= 0: continue
                tx.append({"from": recv_am, "to": m, "amount": int(round(amt)), "reason": amy_name})

        # 일반 이체
        for t in transfers:
            frm, to, amt = t.get("from"), t.get("to"), int(t.get("amount",0))
            memo = t.get("memo","이체")
            if frm and to and amt > 0:
                tx.append({"from": frm, "to": to, "amount": int(amt), "reason": f"이체:{memo}"})

        # 팀비 산식 (별도 표기; 보전 없음)
        sungmo_members_sum = int(round(float(income_sm["amount"].sum()))) if not income_sm.empty else 0
        teamfee_used_sum   = sum(int(x.get("amount",0)) for x in teamfee_items)
        teamfee_balance    = int(sungmo_fixed - sungmo_members_sum - teamfee_used_sum)

        # 팀비 사용: recv_bs → 사용자
        if recv_bs:
            for x in teamfee_items:
                who = x.get("who"); amt = int(x.get("amount",0))
                if who and amt > 0:
                    tx.append({"from": recv_bs, "to": who, "amount": amt, "reason": f"팀비사용:{x.get('memo','')}"})

        # 표시
        if not tx:
            st.info("이번 달 정산에 반영할 항목이 없습니다. (팀비/이체/수입 데이터 확인)")
        else:
            tx_df = pd.DataFrame(tx)
            people = set([*tx_df["from"].unique().tolist(), *tx_df["to"].unique().tolist()])
            balances = {p: 0 for p in people if p}
            for _, r in tx_df.iterrows():
                frm, to, amt = r["from"], r["to"], int(r["amount"])
                balances[frm] = balances.get(frm, 0) - amt
                balances[to]  = balances.get(to, 0) + amt

            net_df = pd.DataFrame([{"사람": k, "순액(만원)": v} for k, v in balances.items()]).sort_values("순액(만원)", ascending=False).reset_index(drop=True)
            st.markdown("##### 사람별 순액(개인 정산)")
            st.dataframe(net_df, use_container_width=True, hide_index=True,
                         column_config={"순액(만원)": st.column_config.NumberColumn(format="%.0f")})

            # 최종 지급 지시서 (recv_bs 기준)
            st.markdown("##### 최종 지급 지시서 (개인 정산)")
            orders = []
            if recv_bs:
                for _, row in net_df.iterrows():
                    person, bal = row["사람"], int(row["순액(만원)"])
                    if person == recv_bs:
                        continue
                    if bal > 0:
                        orders.append({"From": recv_bs, "To": person, "금액(만원)": bal, "비고": "개인 정산"})
                    elif bal < 0:
                        orders.append({"From": person, "To": recv_bs, "금액(만원)": abs(bal), "비고": "개인 정산"})
            orders_df = pd.DataFrame(orders)
            st.dataframe(orders_df, use_container_width=True, hide_index=True,
                         column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})

            # 팀비 (별도 표기)
            st.markdown("##### 팀비 (별도 표기)")
            st.dataframe(pd.DataFrame([{
                "From": "—", "To": "팀비",
                "금액(만원)": teamfee_balance,
                "비고": f"{sm_name}({int(sungmo_fixed)} - {int(sungmo_members_sum)} - {int(teamfee_used_sum)})"
            }]), use_container_width=True, hide_index=True,
            column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})

            # 참고: 위치별 팀원 실수입(해당월)
            with st.expander("참고: 위치별 팀원 실수입(해당월)", expanded=False):
                def _show_income(title, data):
                    st.markdown(f"**{title}**")
                    if data.empty:
                        st.write("- (데이터 없음)")
                    else:
                        view = data.rename(columns={"member":"팀원","amount":"금액(만원)"}).sort_values("금액(만원)", ascending=False)
                        st.dataframe(view, use_container_width=True, hide_index=True,
                                     column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})
                _show_income(bs_name,  income_bs)
                _show_income(sm_name,  income_sm)
                _show_income(amy_name, income_amy)
                _show_income(lee_name, income_lee)
