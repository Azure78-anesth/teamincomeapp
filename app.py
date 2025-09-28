
import streamlit as st
import pandas as pd
from datetime import date, datetime
from typing import List, Dict, Any

# ---------- Page & Global Styles ----------
st.set_page_config(page_title="팀 수입 관리 대시보드", layout="wide")

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

# ---------- Supabase (optional) & Session "DB" ----------
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
    """Supabase가 설정되어 있고 온라인이면 DB에서 로드, 아니면 세션 초기화."""
    if sb:
        try:
            tmem = sb.table("team_members").select("*").order("order").execute().data
            locs = sb.table("locations").select("*").order("order").execute().data
            incs = sb.table("incomes").select("*").order("date").execute().data
            team_members = [{"id":x["id"],"name":x["name"],"order":x.get("order",0)} for x in tmem]
            locations = [{"id":x["id"],"name":x["name"],"category":x.get("category",""),"order":x.get("order",0)} for x in locs]
            income_records = [{
                "id": x["id"], "date": x["date"],
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
    """세션 리스트에 order 필드가 없으면 부여하고 정렬."""
    lst = st.session_state.get(list_key, [])
    changed = False
    for i, x in enumerate(lst):
        if "order" not in x:
            x["order"] = i
            changed = True
    if changed:
        st.session_state[list_key] = lst
    st.session_state[list_key] = sorted(st.session_state[list_key], key=lambda x: x.get("order", 0))

def swap_order(list_key: str, idx_a: int, idx_b: int):
    lst = st.session_state[list_key]
    lst[idx_a]["order"], lst[idx_b]["order"] = lst[idx_b]["order"], lst[idx_a]["order"]
    st.session_state[list_key] = sorted(lst, key=lambda x: x["order"])

# ---------- UI ----------
st.title("팀 수입 관리 대시보드")
if sb:
    st.success("✅ Supabase 연결됨 (팀 공동 사용 가능)")
else:
    st.info("🧪 Supabase 미설정 상태 — 세션 메모리로만 동작합니다(예시 실행용). 팀원이 함께 쓰려면 Secrets에 SUPABASE를 설정하세요.")

load_data()
ensure_order("team_members")
ensure_order("locations")

tab1, tab2, tab3 = st.tabs(["수입 입력", "통계", "설정"])

# ========== Tab 1: 수입 입력 ==========
with tab1:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("수입 입력")
    col1, col2 = st.columns([1,1])
    with col1:
        d = st.date_input("발생일", value=date.today(), format="YYYY-MM-DD")
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

    if st.session_state.income_records:
        st.markdown("#### 최근 입력")
        df_prev = pd.DataFrame([
            {
                "날짜": r["date"],
                "팀원": next((m["name"] for m in st.session_state.team_members if m["id"] == r["teamMemberId"]), ""),
                "업체": next((l["name"] for l in st.session_state.locations if l["id"] == r["locationId"]), ""),
                "금액(만원)": r["amount"],
                "메모": r.get("memo",""),
            } for r in sorted(st.session_state.income_records, key=lambda x: x["date"], reverse=True)[:50]
        ])
        st.dataframe(df_prev, use_container_width=True,
                     column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")})
    st.markdown('</div>', unsafe_allow_html=True)

# ========== Tab 2: 통계 ==========
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
        cur_year = datetime.now().year
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
                    st.markdown("##### 연간 합계")
                    st.dataframe(annual_by_member, use_container_width=True,
                                 column_config={"연간 합계(만원)": st.column_config.NumberColumn(format="%.0f")})

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
                             .sort_values("날짜", descending=False))
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

                    # (참고) 월별 누적(YTD) 테이블
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

# ========== Tab 3: 설정 ==========
with tab3:
    st.subheader("설정")

    # 확인 팝업 상태
    st.session_state.setdefault("confirm_target", None)   # {"type": "member"|"location", "id": "...", "name": "..."}
    st.session_state.setdefault("confirm_action", None)   # "delete"
    def open_confirm(_type, _id, _name, action):
        st.session_state["confirm_target"] = {"type": _type, "id": _id, "name": _name}
        st.session_state["confirm_action"] = action
    def close_confirm():
        st.session_state["confirm_target"] = None
        st.session_state["confirm_action"] = None

    # 확인 팝업 UI (모달 유사)
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
                    st.experimental_rerun()
            with c2:
                if st.button("❌ 취소", use_container_width=True):
                    close_confirm()
                    st.experimental_rerun()

    # 팀원 관리
    st.markdown("### 👤 팀원 관리")
    with st.form("add_member_form", clear_on_submit=True):
        new_member = st.text_input("이름", "")
        submitted = st.form_submit_button("팀원 추가")
        if submitted:
            if new_member.strip():
                mid = f"m_{datetime.utcnow().timestamp()}"
                upsert_row("team_members", {"id": mid, "name": new_member.strip(), "order": len(st.session_state.team_members)})
                st.success("팀원 추가 완료")
            else:
                st.error("이름을 입력하세요.")

    if st.session_state.team_members:
        st.markdown("#### 팀원 목록 (순서 이동/삭제)")
        tm = sorted(st.session_state.team_members, key=lambda x: x.get("order",0))
        hc1, hc2, hc3, hc4 = st.columns([6, 1.2, 1.2, 1.2])
        hc1.write("이름"); hc2.write("위로"); hc3.write("아래로"); hc4.write("삭제")
        for i, m in enumerate(tm):
            c1, c2, c3, c4 = st.columns([6, 1.2, 1.2, 1.2])
            c1.write(f"**{m['name']}**")
            with c2:
                if st.button("▲", key=f"member_up_{m['id']}", disabled=(i==0)):
                    if i > 0:
                        idx_a = i; idx_b = i-1
                        ids = [x["id"] for x in tm]
                        a_id, b_id = ids[idx_a], ids[idx_b]
                        orig = st.session_state.team_members
                        ia = next(j for j,x in enumerate(orig) if x["id"]==a_id)
                        ib = next(j for j,x in enumerate(orig) if x["id"]==b_id)
                        swap_order("team_members", ia, ib)
                        st.experimental_rerun()
            with c3:
                if st.button("▼", key=f"member_down_{m['id']}", disabled=(i==len(tm)-1)):
                    if i < len(tm)-1:
                        idx_a = i; idx_b = i+1
                        ids = [x["id"] for x in tm]
                        a_id, b_id = ids[idx_a], ids[idx_b]
                        orig = st.session_state.team_members
                        ia = next(j for j,x in enumerate(orig) if x["id"]==a_id)
                        ib = next(j for j,x in enumerate(orig) if x["id"]==b_id)
                        swap_order("team_members", ia, ib)
                        st.experimental_rerun()
            with c4:
                if st.button("🗑️", key=f"member_del_{m['id']}"):
                    open_confirm("member", m["id"], m["name"], "delete")
                    st.experimental_rerun()
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
                upsert_row("locations", {"id": lid, "name": loc_name.strip(), "category": loc_cat, "order": len(st.session_state.locations)})
                st.success("업체 추가 완료")
            else:
                st.error("업체명을 입력하세요.")

    if st.session_state.locations:
        st.markdown("#### 업체 목록 (순서 이동/삭제)")
        locs = sorted(st.session_state.locations, key=lambda x: x.get("order",0))
        h1,h2,h3,h4,h5 = st.columns([5.5,2.2,1.1,1.1,1.1])
        h1.write("업체명"); h2.write("분류"); h3.write("위로"); h4.write("아래로"); h5.write("삭제")
        for i, l in enumerate(locs):
            c1, c2, c3, c4, c5 = st.columns([5.5,2.2,1.1,1.1,1.1])
            c1.write(f"**{l['name']}**"); c2.write(l.get("category",""))
            with c3:
                if st.button("▲", key=f"loc_up_{l['id']}", disabled=(i==0)):
                    if i > 0:
                        idx_a = i; idx_b = i-1
                        ids = [x["id"] for x in locs]
                        a_id, b_id = ids[idx_a], ids[idx_b]
                        orig = st.session_state.locations
                        ia = next(j for j,x in enumerate(orig) if x["id"]==a_id)
                        ib = next(j for j,x in enumerate(orig) if x["id"]==b_id)
                        swap_order("locations", ia, ib)
                        st.experimental_rerun()
            with c4:
                if st.button("▼", key=f"loc_down_{l['id']}", disabled=(i==len(locs)-1)):
                    if i < len(locs)-1:
                        idx_a = i; idx_b = i+1
                        ids = [x["id"] for x in locs]
                        a_id, b_id = ids[idx_a], ids[idx_b]
                        orig = st.session_state.locations
                        ia = next(j for j,x in enumerate(orig) if x["id"]==a_id)
                        ib = next(j for j,x in enumerate(orig) if x["id"]==b_id)
                        swap_order("locations", ia, ib)
                        st.experimental_rerun()
            with c5:
                if st.button("🗑️", key=f"loc_del_{l['id']}"):
                    open_confirm("location", l["id"], l["name"], "delete")
                    st.experimental_rerun()
    else:
        st.info("등록된 업체가 없습니다.")

    st.divider()
    if st.button("데이터 새로고침"):
        load_data()
        st.success("새로고침 완료")
