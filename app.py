
import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo  # 한국 시간대 지원
NOW_KST = datetime.now(ZoneInfo("Asia/Seoul"))

from typing import List, Dict, Any

# ============================
# Page & Global Styles
# ============================
st.set_page_config(page_title="팀 수입 관리 프로그램", layout="wide")

st.markdown("""
<style>
/* Global readability */
html, body, [class*="css"]  { font-size: 16px; }
h1, h2, h3 { letter-spacing: 0.2px; }
section.main > div { padding-top: 0.6rem; }
/* Card-like container */
.block { padding: 1rem 1.25rem; border: 1px solid #e5e7eb; border-radius: 14px; background: #fff; }
/* Align numeric */
.mono { font-variant-numeric: tabular-nums; }
/* Tables: keep single-line cells */
.dataframe td, .dataframe th { white-space: nowrap; }
/* Tabs spacing */
.stTabs [role="tablist"] { margin-bottom: 0.25rem; }
/* Buttons */
button[kind="secondary"], button[kind="primary"] { min-height: 38px }
</style>
""", unsafe_allow_html=True)

# ============================
# Supabase client (optional)
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
    """Supabase가 설정되어 있으면 DB에서 로드, 아니면 세션 초기화."""
    if sb:
        try:
            tmem = sb.table("team_members").select("*").order("order").execute().data
            locs = sb.table("locations").select("*").order("order").execute().data
            # incomes는 많은 경우가 있어 날짜 기준으로 로드
            incs = sb.table("incomes").select("*").order("date").execute().data
            team_members = [{"id":x["id"],"name":x["name"],"order":x.get("order",0)} for x in tmem]
            locations = [{"id":x["id"],"name":x["name"],"category":x.get("category",""),"order":x.get("order",0)} for x in locs]
            income_records = [{
                "id": x["id"],
                "date": x["date"],
                "teamMemberId": x.get("team_member_id"),
                "locationId": x.get("location_id"),
                "amount": float(x["amount"]),
                "memo": x.get("memo",""),
            } for x in incs]
            st.session_state.team_members = team_members
            st.session_state.locations = locations
            st.session_state.income_records = income_records
        except Exception:
            st.warning("오프라인(또는 Supabase 오류) 감지 → 임시 메모리 모드로 전환합니다.")
            init_state()
    else:
        init_state()

def upsert_row(table: str, payload: Dict[str, Any]):
    """Supabase 쓰기 실패 시 자동으로 세션 메모리에 저장."""
    if sb:
        try:
            if table == "incomes":
                sb.table("incomes").insert({
                    "id": payload["id"],
                    "date": payload["date"],
                    "team_member_id": payload["teamMemberId"],
                    "location_id": payload["locationId"],
                    "amount": payload["amount"],
                    "memo": payload.get("memo",""),
                }).execute()
            elif table == "team_members":
                sb.table("team_members").insert({
                    "id": payload["id"],
                    "name": payload["name"],
                    "order": payload.get("order",0),
                }).execute()
            elif table == "locations":
                sb.table("locations").insert({
                    "id": payload["id"],
                    "name": payload["name"],
                    "category": payload["category"],
                    "order": payload.get("order",0),
                }).execute()
            load_data()
            return
        except Exception:
            st.warning("Supabase 기록 실패(오프라인?) → 임시 메모리에 저장합니다.")
    # fallback
    if table == "incomes":
        st.session_state.income_records.append(payload)
    elif table == "team_members":
        st.session_state.team_members.append(payload)
    elif table == "locations":
        st.session_state.locations.append(payload)

def update_income(id_value: str, payload: dict):
    """수입 레코드 업데이트 (DB 있으면 update, 없으면 세션 수정)."""
    if sb:
        try:
            sb.table("incomes").update({
                "date": payload["date"],
                "team_member_id": payload["teamMemberId"],
                "location_id": payload["locationId"],
                "amount": payload["amount"],
                "memo": payload.get("memo",""),
            }).eq("id", id_value).execute()
            load_data()
            return
        except Exception:
            st.warning("Supabase 업데이트 실패(오프라인?) → 임시 메모리에만 반영합니다.")
    # fallback
    for r in st.session_state.income_records:
        if r["id"] == id_value:
            r.update({
                "date": payload["date"],
                "teamMemberId": payload["teamMemberId"],
                "locationId": payload["locationId"],
                "amount": float(payload["amount"]),
                "memo": payload.get("memo",""),
            })
            break

def delete_row(table: str, id_value: str):
    if sb:
        try:
            sb.table(table).delete().eq("id", id_value).execute()
            load_data()
            return
        except Exception:
            st.warning("Supabase 삭제 실패(오프라인?) → 임시 메모리에서만 삭제합니다.")
    # fallback
    if table == "incomes":
        st.session_state.income_records = [r for r in st.session_state.income_records if r["id"] != id_value]
    elif table == "team_members":
        st.session_state.team_members = [r for r in st.session_state.team_members if r["id"] != id_value]
    elif table == "locations":
        st.session_state.locations = [r for r in st.session_state.locations if r["id"] != id_value]

def ensure_order(list_key: str):
    """
    리스트의 order를 0..n-1로 재부여하여 정규화.
    DB(Supabase)에도 반영하여 새로고침에도 유지.
    """
    lst = st.session_state.get(list_key, [])
    lst_sorted = sorted(lst, key=lambda x: x.get("order", 0))
    changed = False
    for i, x in enumerate(lst_sorted):
        if x.get("order") != i:
            x["order"] = i
            changed = True

    st.session_state[list_key] = lst_sorted
    if changed and sb:
        table = "team_members" if list_key == "team_members" else "locations"
        try:
            for x in lst_sorted:
                sb.table(table).update({"order": x["order"]}).eq("id", x["id"]).execute()
        except Exception:
            st.warning(f"{table} order 정규화 저장 실패(네트워크/권한)")

def swap_order(list_key: str, idx_a: int, idx_b: int):
    """
    보이는 리스트(정렬된)에서의 인덱스를 기준으로 순서를 교환.
    DB 업데이트 → 다시 로드 → 정규화 → rerun
    """
    lst = st.session_state[list_key]
    a, b = lst[idx_a], lst[idx_b]
    a_order, b_order = a.get("order", 0), b.get("order", 0)
    a["order"], b["order"] = b_order, a_order
    st.session_state[list_key] = sorted(lst, key=lambda x: x["order"])

    if sb:
        table = "team_members" if list_key == "team_members" else "locations"
        try:
            sb.table(table).update({"order": a["order"]}).eq("id", a["id"]).execute()
            sb.table(table).update({"order": b["order"]}).eq("id", b["id"]).execute()
        except Exception:
            st.warning("순서 저장 실패(네트워크/권한) — 화면에는 반영됐지만 새로고침 시 되돌 수 있음")

    load_data()
    ensure_order(list_key)
    st.rerun()

# ============================
# Bootstrapping
# ============================
st.title("팀 수입 관리 프로그램")
if sb:
    st.success("✅ Supabase 연결됨 (팀 공동 사용 가능)")
else:
    st.info("🧪 Supabase 미설정 상태 — 세션 메모리로만 동작합니다(예시 실행용). 팀원이 함께 쓰려면 Secrets에 SUPABASE를 설정하세요.")

load_data()
ensure_order("team_members")
ensure_order("locations")

# 상태 초기화
st.session_state.setdefault("confirm_target", None)  # 삭제 모달용
st.session_state.setdefault("confirm_action", None)
st.session_state.setdefault("edit_income_id", None)
st.session_state.setdefault("confirm_delete_income_id", None)
st.session_state.setdefault("records_page", 0)

tab1, tab2, tab3, tab4 = st.tabs(["수입 입력", "통계", "설정", "기록 관리"])

# ============================
# Tab 1: 수입 입력
# ============================
with tab1:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("수입 입력")
    col1, col2 = st.columns([1,1])
    with col1:
        # 발생일 위젯 상태 동기화
        if "input_date" not in st.session_state:
            st.session_state.input_date = NOW_KST.date()
        else:
            # 하루가 바뀌면 자동으로 리셋
            if st.session_state.input_date != NOW_KST.date():
                st.session_state.input_date = NOW_KST.date()

        d = st.date_input(
            "발생일",
            key="input_date",
            value=st.session_state.input_date,
            format="YYYY-MM-DD"
        )

        member_options = {m["name"]: m["id"] for m in st.session_state.team_members}
        member_name = st.selectbox("팀원", list(member_options.keys()) if member_options else ["(팀원을 먼저 추가하세요)"])
        member_id = member_options.get(member_name)

    with col2:
        cat = st.radio("업체 분류", ["보험", "비보험"], horizontal=True)
        filtered_locations = [l for l in st.session_state.locations if l["category"] == cat]
        loc_options = {l["name"]: l["id"] for l in filtered_locations}
        if not loc_options:
            st.warning(f"'{cat}' 분류 업체가 없습니다. 설정 탭에서 추가하세요.")
        loc_name = st.selectbox("업체", list(loc_options.keys()) if loc_options else [])
        loc_id = loc_options.get(loc_name)

    # 금액 입력(빈 칸 + 숫자만)
    amount_raw = st.text_input("금액(만원 단위)", value="", placeholder="예: 50 (만원)")
    try:
        amount = float(amount_raw.replace(",", "").strip()) if amount_raw.strip() != "" else None
    except ValueError:
        amount = None
        st.error("금액은 숫자만 입력하세요. (예: 50)")

    memo = st.text_input("메모(선택)", "")

    if st.button("등록하기", type="primary"):
        if not (member_id and loc_id and d and (amount is not None and amount > 0)):
            st.error("모든 필드를 올바르게 입력하세요.")
        else:
            rid = f"inc_{datetime.utcnow().timestamp()}"
            upsert_row("incomes", {
                "id": rid,
                "date": d.strftime("%Y-%m-%d"),
                "teamMemberId": member_id,
                "locationId": loc_id,
                "amount": float(amount),
                "memo": memo,
            })
            st.success("저장되었습니다 ✅")

    # 최근 입력 + 수정 버튼 (간단 미리보기)
    if st.session_state.income_records:
        st.markdown("#### 최근 입력")
        recent = sorted(st.session_state.income_records, key=lambda x: x["date"], reverse=True)[:50]
        df_prev = pd.DataFrame([
            {
                "날짜": r["date"],
                "팀원": next((m["name"] for m in st.session_state.team_members if m["id"] == r["teamMemberId"]), ""),
                "업체": next((l["name"] for l in st.session_state.locations if l["id"] == r["locationId"]), ""),
                "금액(만원)": r["amount"],
                "메모": r.get("memo",""),
            } for r in recent
        ])
        st.dataframe(df_prev, use_container_width=True,
                     column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})
    st.markdown('</div>', unsafe_allow_html=True)

# ============================
# Tab 2: 통계
# ============================
with tab2:
    st.subheader("통계")

    def resolve_name(id_value: str, coll: List[Dict[str,Any]]) -> str:
        for x in coll:
            if x["id"] == id_value: return x.get("name","")
        return ""

    records = st.session_state.get("income_records", [])
    if not records:
        st.info("데이터가 없습니다. 먼저 [수입 입력]에서 데이터를 추가해 주세요.")
    else:
        df = pd.DataFrame([
            {
                "date": r.get("date"),
                "amount": r.get("amount"),
                "member": resolve_name(r.get("teamMemberId",""), st.session_state.team_members),
                "location": resolve_name(r.get("locationId",""), st.session_state.locations),
                "category": next((l["category"] for l in st.session_state.locations if l["id"] == r.get("locationId")), ""),
            } for r in records
        ])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()
        df["year"] = df["date"].dt.year.astype(int)
        df["month"] = df["date"].dt.month.astype(int)
        df["day"] = df["date"].dt.strftime("%Y-%m-%d")

        years = sorted(df["year"].unique().tolist())
        cur_year = NOW_KST.year
        default_year = cur_year if cur_year in years else years[-1]

        c1, c2 = st.columns([3,2])
        with c1:
            year = st.selectbox("연도(연간 리셋/독립 집계)", years, index=years.index(default_year))
        with c2:
            st.caption("선택 연도 외 데이터는 저장만 유지(열람 전용)")

        dfY = df[df["year"] == year].copy()
        if dfY.empty:
            st.warning(f"{year}년 데이터가 없습니다.")
        else:
            tab_mem, tab_loc = st.tabs(["팀원별", "업장별"])

            # ----- 팀원별 -----
            with tab_mem:
                st.markdown('<div class="block">', unsafe_allow_html=True)
                st.markdown("#### 팀원별 수입 통계")

                members = sorted([m for m in dfY["member"].dropna().unique().tolist() if m])
                member_select = st.selectbox("팀원 선택(최상단은 비교 보기)",
                                             ["팀원 비교(전체)"] + members, index=0)

                if member_select == "팀원 비교(전체)":
                    annual_by_member = (
    dfY.groupby("member", dropna=False)["amount"]
    .sum().sort_values(ascending=False).reset_index()
    .rename(columns={"member":"팀원","amount":"연간 합계(만원)"})
)

# 👉 순위 컬럼 추가 (1부터 시작)
annual_by_member.insert(0, "순위", range(1, len(annual_by_member) + 1))

st.markdown("##### 연간 합계")
st.dataframe(
    annual_by_member.set_index("순위"),
    use_container_width=True,
    column_config={"연간 합계(만원)": st.column_config.NumberColumn(format="%.0f")}
)

                    months_avail_all = sorted(dfY["month"].unique().tolist())
                    month_sel2 = st.selectbox("월 선택(보험/비보험 분리 보기)", months_avail_all,
                                              index=len(months_avail_all)-1)

                    df_month = dfY[dfY["month"] == month_sel2].copy()
                    by_mem_cat = df_month.groupby(["member","category"], dropna=False)["amount"].sum().reset_index()
                    pivot = by_mem_cat.pivot(index="member", columns="category", values="amount").fillna(0.0)
                    for col in ["보험","비보험"]:
                        if col not in pivot.columns: pivot[col] = 0.0
                    pivot = pivot[["보험","비보험"]]
                    pivot["총합(만원)"] = pivot["보험"] + pivot["비보험"]
                    pivot = pivot.sort_values("총합(만원)", ascending=False)
                    pivot.index.name = "팀원"

                    st.markdown(f"##### {month_sel2}월 · 보험/비보험 분리 + 총합")
                    st.dataframe(pivot, use_container_width=True,
                                 column_config={c: st.column_config.NumberColumn(format="%.0f")
                                                for c in ["보험","비보험","총합(만원)"]})
                else:
                    dfM = dfY[dfY["member"] == member_select].copy()
                    months_avail = sorted(dfM["month"].unique().tolist()) or list(range(1,13))
                    month_sel = st.selectbox("월 선택(일별 상세용)", months_avail, index=len(months_avail)-1)

                    k1,k2,k3 = st.columns([1,1,1])
                    k1.metric("연간 합계(만원)", f"{dfM['amount'].sum():,.0f}")
                    k2.metric(f"{month_sel}월 합계(만원)", f"{dfM.loc[dfM['month']==month_sel,'amount'].sum():,.0f}")
                    k3.metric("건수(연간)", int(len(dfM)))

                    daily = (dfM[dfM["month"]==month_sel].groupby("day", dropna=False)["amount"]
                             .sum().reset_index().rename(columns={"day":"날짜","amount":"금액(만원)"})
                             .sort_values("날짜"))
                    st.markdown(f"##### {member_select} · {month_sel}월 일별 합계")
                    st.dataframe(daily, use_container_width=True,
                                 column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})

                    monthly = (dfM.groupby("month", dropna=False)["amount"]
                               .sum().reset_index().rename(columns={"month":"월","amount":"합계(만원)"})
                               .sort_values("월"))
                    st.markdown(f"##### {member_select} · 월별 합계(연간)")
                    st.dataframe(monthly, use_container_width=True,
                                 column_config={"합계(만원)": st.column_config.NumberColumn(format="%.0f")})
                st.markdown('</div>', unsafe_allow_html=True)

            # ----- 업장별 -----
            with tab_loc:
                st.markdown('<div class="block">', unsafe_allow_html=True)
                st.markdown("#### 업장별 통계 (보험/비보험 분리)")

                cat_sel = st.radio("분류 선택", ["보험","비보험"], horizontal=True)
                dfC = dfY[dfY["category"] == cat_sel].copy()
                if dfC.empty:
                    st.warning(f"{year}년 {cat_sel} 데이터가 없습니다.")
                else:
                    rank_mode = st.radio("랭킹 모드", ["연간 순위","월별 순위"], horizontal=True, index=0)

                    if rank_mode == "연간 순위":
                        annual_loc = (dfC.groupby("location", dropna=False)["amount"].sum().reset_index()
                                      .rename(columns={"location":"업체","amount":"연간합계(만원)"})
                                      .sort_values("연간합계(만원)", ascending=False).reset_index(drop=True))
                        annual_loc.insert(0, "순위", annual_loc.index + 1)
                        st.markdown(f"##### {cat_sel} · 연간 순위")
                        st.dataframe(annual_loc[["순위","업체","연간합계(만원)"]], use_container_width=True,
                                     column_config={"연간합계(만원)": st.column_config.NumberColumn(format="%.0f")})
                    else:
                        months_avail_c = sorted(dfC["month"].unique().tolist())
                        month_rank = st.selectbox("월 선택(해당 월만 표시)", months_avail_c, index=len(months_avail_c)-1)
                        df_month = dfC[dfC["month"] == month_rank].copy()
                        monthly_loc = (df_month.groupby("location", dropna=False)["amount"].sum().reset_index()
                                       .rename(columns={"location":"업체","amount":"월합계(만원)"})
                                       .sort_values("월합계(만원)", ascending=False).reset_index(drop=True))
                        monthly_loc.insert(0, "순위", monthly_loc.index + 1)
                        st.markdown(f"##### {cat_sel} · {month_rank}월 순위 (해당 월만)")
                        st.dataframe(monthly_loc[["순위","업체","월합계(만원)"]], use_container_width=True,
                                     column_config={"월합계(만원)": st.column_config.NumberColumn(format="%.0f")})

                    # 참고: 월별 누적(YTD)
                    by_loc_month = (dfC.groupby(["location","month"], dropna=False)["amount"].sum()
                                    .reset_index().sort_values(["location","month"]))
                    by_loc_month["월누적(YTD)"] = by_loc_month.groupby("location")["amount"].cumsum()
                    ytd_wide = by_loc_month.pivot(index="location", columns="month", values="월누적(YTD)").fillna(0.0)
                    ytd_wide.columns = [f"{m}월" for m in ytd_wide.columns]
                    ytd_wide = ytd_wide.sort_values(ytd_wide.columns[-1], ascending=False)
                    ytd_wide.index.name = "업체"
                    st.markdown("##### 월별 누적(YTD) 테이블(참고)")
                    st.dataframe(ytd_wide, use_container_width=True)
                    st.caption("※ '월별 누적(YTD)'은 해당 연도 1월부터 선택 월까지의 누적 합계입니다.")
                st.markdown('</div>', unsafe_allow_html=True)

# ============================
# Tab 3: 설정 (추가/삭제/순서 이동)
# ============================
with tab3:
    st.subheader("설정")

    # 확인 팝업 상태 핸들러
    def open_confirm(_type, _id, _name, action):
        st.session_state["confirm_target"] = {"type": _type, "id": _id, "name": _name}
        st.session_state["confirm_action"] = action
    def close_confirm():
        st.session_state["confirm_target"] = None
        st.session_state["confirm_action"] = None

    # 팝업 UI
    if st.session_state["confirm_target"]:
        tgt = st.session_state["confirm_target"]
        action = st.session_state["confirm_action"]
        with st.container(border=True):
            st.warning(f"정말로 **{tgt['name']}** 을(를) **{'삭제' if action=='delete' else action}** 하시겠습니까?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 확인", use_container_width=True):
                    if action == "delete":
                        if tgt["type"] == "member":
                            delete_row("team_members", tgt["id"])
                        elif tgt["type"] == "location":
                            delete_row("locations", tgt["id"])
                    close_confirm()
                    st.rerun()
            with c2:
                if st.button("❌ 취소", use_container_width=True):
                    close_confirm()
                    st.rerun()

    # 팀원 관리
    st.markdown("### 👤 팀원 관리")
    with st.form("add_member_form", clear_on_submit=True):
        new_member = st.text_input("이름", "")
        submitted = st.form_submit_button("팀원 추가")
        if submitted:
            if new_member.strip():
                mid = f"m_{datetime.utcnow().timestamp()}"
                next_order = (max([x.get("order",0) for x in st.session_state.team_members] or [-1]) + 1)
                upsert_row("team_members", {"id": mid, "name": new_member.strip(), "order": next_order})
                st.success("팀원 추가 완료")
            else:
                st.error("이름을 입력하세요.")

    if st.session_state.team_members:
        st.markdown("#### 팀원 목록 (순서 이동/삭제)")
        tm = st.session_state.team_members  # ensure_order로 이미 정렬된 상태
        hc1, hc2, hc3, hc4 = st.columns([6, 1.2, 1.2, 1.2])
        hc1.write("이름"); hc2.write("위로"); hc3.write("아래로"); hc4.write("삭제")
        for i, m in enumerate(tm):
            c1, c2, c3, c4 = st.columns([6, 1.2, 1.2, 1.2])
            c1.write(f"**{m['name']}**")
            with c2:
                if st.button("▲", key=f"member_up_{m['id']}", disabled=(i==0)):
                    swap_order("team_members", i, i-1)
            with c3:
                if st.button("▼", key=f"member_down_{m['id']}", disabled=(i==len(tm)-1)):
                    swap_order("team_members", i, i+1)
            with c4:
                if st.button("🗑️", key=f"member_del_{m['id']}"):
                    open_confirm("member", m["id"], m["name"], "delete")
                    st.rerun()
    else:
        st.info("등록된 팀원이 없습니다.")

    st.divider()

    # 업체 관리
    st.markdown("### 🏢 업체 관리")
    with st.form("add_location_form", clear_on_submit=True):
        loc_name = st.text_input("업체명", "")
        loc_cat = st.selectbox("분류", ["보험", "비보험"])
        submitted = st.form_submit_button("업체 추가")
        if submitted:
            if loc_name.strip():
                lid = f"l_{datetime.utcnow().timestamp()}"
                next_order = (max([x.get("order",0) for x in st.session_state.locations] or [-1]) + 1)
                upsert_row("locations", {"id": lid, "name": loc_name.strip(), "category": loc_cat, "order": next_order})
                st.success("업체 추가 완료")
            else:
                st.error("업체명을 입력하세요.")

    if st.session_state.locations:
        st.markdown("#### 업체 목록 (순서 이동/삭제)")
        locs = st.session_state.locations  # ensure_order로 이미 정렬된 상태
        h1,h2,h3,h4,h5 = st.columns([5.5,2.2,1.1,1.1,1.1])
        h1.write("업체명"); h2.write("분류"); h3.write("위로"); h4.write("아래로"); h5.write("삭제")
        for i, l in enumerate(locs):
            c1, c2, c3, c4, c5 = st.columns([5.5,2.2,1.1,1.1,1.1])
            c1.write(f"**{l['name']}**"); c2.write(l.get("category",""))
            with c3:
                if st.button("▲", key=f"loc_up_{l['id']}", disabled=(i==0)):
                    swap_order("locations", i, i-1)
            with c4:
                if st.button("▼", key=f"loc_down_{l['id']}", disabled=(i==len(locs)-1)):
                    swap_order("locations", i, i+1)
            with c5:
                if st.button("🗑️", key=f"loc_del_{l['id']}"):
                    open_confirm("location", l["id"], l["name"], "delete")
                    st.rerun()
    else:
        st.info("등록된 업체가 없습니다.")

    st.divider()
    if st.button("데이터 새로고침"):
        load_data()
        st.success("새로고침 완료")
        st.rerun()

# ============================
# Tab 4: 기록 관리 (전체 수정/삭제)
# ============================
with tab4:
    st.subheader("기록 관리 (전체 수정/삭제)")

    def resolve_name2(id_value: str, coll: list[dict]) -> str:
        for x in coll:
            if x["id"] == id_value:
                return x.get("name", "")
        return ""

    records = st.session_state.get("income_records", [])
    if not records:
        st.info("데이터가 없습니다. 먼저 [수입 입력]에서 데이터를 추가해 주세요.")
        st.stop()

    df = pd.DataFrame([
        {
            "id": r.get("id"),
            "date": r.get("date"),
            "amount": pd.to_numeric(r.get("amount"), errors="coerce"),
            "member_id": r.get("teamMemberId"),
            "member": resolve_name2(r.get("teamMemberId",""), st.session_state.team_members),
            "location_id": r.get("locationId"),
            "location": resolve_name2(r.get("locationId",""), st.session_state.locations),
            "category": next((l["category"] for l in st.session_state.locations if l["id"] == r.get("locationId")), ""),
            "memo": r.get("memo",""),
        } for r in records
    ])
    df["amount"] = df["amount"].fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["year"] = df["date"].dt.year
    df["day"] = df["date"].dt.strftime("%Y-%m-%d")

    years = sorted(df["year"].unique().tolist())
    c1, c2, c3 = st.columns([2,3,2])
    with c1:
        year_sel = st.selectbox("연도", years, index=len(years)-1)
    dmin = df.loc[df["year"]==year_sel, "date"].min().date()
    dmax = df.loc[df["year"]==year_sel, "date"].max().date()
    with c2:
        date_range = st.date_input("기간", value=(dmin, dmax), min_value=dmin, max_value=dmax, format="YYYY-MM-DD")
    with c3:
        order_by = st.selectbox("정렬", ["날짜↓(최신)", "날짜↑", "금액↓", "금액↑"])

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
    if mem_sel != "전체":
        q = q[q["member"] == mem_sel]
    if cat_sel != "전체":
        q = q[q["category"] == cat_sel]
    if loc_sel != "전체":
        q = q[q["location"] == loc_sel]

    if order_by == "날짜↓(최신)":
        q = q.sort_values(["date","id"], ascending=[False, True])
    elif order_by == "날짜↑":
        q = q.sort_values(["date","id"], ascending=[True, True])
    elif order_by == "금액↓":
        q = q.sort_values(["amount","date"], ascending=[False, False])
    else:
        q = q.sort_values(["amount","date"], ascending=[True, False])

    PAGE_SIZE = 20
    total = len(q)
    total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
    st.session_state.records_page = min(st.session_state.records_page, total_pages-1)
    st.session_state.records_page = max(st.session_state.records_page, 0)

    pc1, pc2, pc3 = st.columns([1,2,1])
    with pc1:
        if st.button("⬅ 이전", disabled=(st.session_state.records_page==0)):
            st.session_state.records_page -= 1
            st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center'>페이지 {st.session_state.records_page+1} / {total_pages} (총 {total}건)</div>", unsafe_allow_html=True)
    with pc3:
        if st.button("다음 ➡", disabled=(st.session_state.records_page>=total_pages-1)):
            st.session_state.records_page += 1
            st.rerun()

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
                        st.session_state.edit_income_id = row["id"]
                        st.rerun()
                with col_b:
                    if st.button("🗑 삭제", key=f"del_any_{row['id']}"):
                        st.session_state.confirm_delete_income_id = row["id"]
                        st.rerun()

    # 삭제 확인
    if st.session_state.confirm_delete_income_id:
        rid = st.session_state.confirm_delete_income_id
        with st.container(border=True):
            st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 삭제 확정"):
                    delete_row("incomes", rid)
                    st.session_state.confirm_delete_income_id = None
                    st.success("삭제되었습니다.")
                    st.rerun()
            with c2:
                if st.button("❌ 취소"):
                    st.session_state.confirm_delete_income_id = None
                    st.rerun()

    # 편집 폼
    if st.session_state.edit_income_id:
        target = next((x for x in st.session_state.income_records if x["id"] == st.session_state.edit_income_id), None)
        if target:
            st.markdown("#### 선택한 기록 수정")
            cur_member = resolve_name2(target["teamMemberId"], st.session_state.team_members)
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
                    if cur_loc["name"] in names:
                        default_loc_idx = names.index(cur_loc["name"])
                loc_name_edit = st.selectbox("업체", list(loc_options.keys()), index=default_loc_idx, key="edit_any_loc")
                loc_id_edit = loc_options[loc_name_edit]

            amount_raw_edit = st.text_input("금액(만원 단위)", value=str(int(float(target["amount"]))), placeholder="예: 50 (만원)", key="edit_any_amount")
            try:
                amount_edit = float(amount_raw_edit.replace(",", "").strip())
            except ValueError:
                amount_edit = None
                st.error("금액은 숫자만 입력하세요. (예: 50)")
            memo_edit = st.text_input("메모(선택)", value=target.get("memo",""), key="edit_any_memo")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅ 저장", type="primary", key="edit_any_save"):
                    if amount_edit is None or amount_edit <= 0:
                        st.error("금액을 올바르게 입력하세요.")
                    else:
                        update_income(
                            target["id"],
                            {
                                "date": new_date.strftime("%Y-%m-%d"),
                                "teamMemberId": member_id_edit,
                                "locationId": loc_id_edit,
                                "amount": float(amount_edit),
                                "memo": memo_edit,
                            }
                        )
                        st.session_state.edit_income_id = None
                        st.success("수정되었습니다.")
                        st.rerun()
            with b2:
                if st.button("❌ 취소", key="edit_any_cancel"):
                    st.session_state.edit_income_id = None
                    st.rerun()
