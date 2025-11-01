import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List
import requests

# ─────────────────────────────────────────
# Global: 한국 시간 오늘
# ─────────────────────────────────────────
NOW_KST = datetime.now(ZoneInfo("Asia/Seoul"))

# ============================
# Page & Styles (모바일 최적화)
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
html, body, [class*="css"]{ font-size:16px; color:var(--text); background:var(--bg); }
section.main > div { padding-top:.6rem; }
h1,h2,h3 { letter-spacing:.2px; margin-top:.25rem; margin-bottom:.5rem; }
/* (기존 스타일 나머지는 생략) */
</style>
""", unsafe_allow_html=True)

# ============================
# Helpers
# ============================
def metric_cards(items: list[tuple[str, str]]):
    parts = ['<div class="mgrid">']
    for title, value in items:
        parts.append(f'<div class="mcard"><div class="mtitle">{title}</div><div class="mvalue">{value}</div></div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)

# ============================
# Supabase 연결
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
        return None

sb = get_supabase_client()

# ============================
# invoices 테이블 자동 생성(있으면 통과)
# ============================
def ensure_invoices_table():
    if not sb:
        return
    try:
        sb.table("invoices").select("id").limit(1).execute()
        return
    except Exception:
        # 없는 경우만 생성 시도 (REST RPC로 SQL 실행)
        try:
            url = st.secrets["SUPABASE_URL"] + "/rest/v1/rpc"
            headers = {
                "apikey": st.secrets["SUPABASE_ANON_KEY"],
                "Authorization": f"Bearer {st.secrets['SUPABASE_ANON_KEY']}",
                "Content-Type": "application/json",
            }
            ddl = """
            create table if not exists public.invoices (
              id uuid primary key default gen_random_uuid(),
              ym text not null,
              team_member_id text references public.team_members(id),
              location_id text references public.locations(id),
              ins_type text,
              issue_amount double precision default 0,
              tax_amount double precision default 0,
              created_at timestamptz default now()
            );
            alter table public.invoices enable row level security;
            create policy if not exists "anon_select_invoices"
              on public.invoices for select to anon using (true);
            create policy if not exists "anon_insert_invoices"
              on public.invoices for insert to anon with check (true);
            create policy if not exists "anon_update_invoices"
              on public.invoices for update to anon using (true) with check (true);
            create policy if not exists "anon_delete_invoices"
              on public.invoices for delete to anon using (true);
            """
            requests.post(url, headers=headers, json={"query": ddl}, timeout=10)
        except Exception:
            # 콘솔에서 이미 생성해 둔 경우가 대부분이므로 조용히 패스
            pass

if sb:
    ensure_invoices_table()

# ============================
# SAFE BOOT: 세션 키 보장
# ============================
ss = st.session_state
ss.setdefault("team_members", [])
ss.setdefault("locations", [])
ss.setdefault("income_records", [])
ss.setdefault("invoice_records", [])
ss.setdefault("confirm_target", None)
ss.setdefault("confirm_action", None)
ss.setdefault("edit_income_id", None)
ss.setdefault("confirm_delete_income_id", None)
ss.setdefault("records_page", 0)

# ============================
# PRIME FROM DB: 도입부에서 즉시 DB → 세션 채우기
#  - 아래에 별도로 load_data()/load_invoices가 있어도 중복 문제 없음
#  - 이미 값이 있으면 덮어쓰지 않고 유지
# ============================
def _prime_from_db():
    if not sb:
        return
    # team_members
    try:
        if not ss["team_members"]:
            rows = sb.table("team_members").select("*").order("order").execute().data or []
            ss["team_members"] = [{"id": r["id"], "name": r["name"], "order": r.get("order", 0)} for r in rows]
    except Exception:
        pass
    # locations
    try:
        if not ss["locations"]:
            rows = sb.table("locations").select("*").order("order").execute().data or []
            ss["locations"] = [{
                "id": r["id"], "name": r["name"],
                "category": r.get("category",""), "order": r.get("order",0)
            } for r in rows]
    except Exception:
        pass
    # incomes (선택)
    try:
        if not ss["income_records"]:
            rows = sb.table("incomes").select("*").order("date").execute().data or []
            ss["income_records"] = [{
                "id": r["id"], "date": r["date"],
                "teamMemberId": r.get("team_member_id"),
                "locationId": r.get("location_id"),
                "amount": float(r.get("amount", 0)),
                "memo": r.get("memo",""),
            } for r in rows]
    except Exception:
        pass
    # invoices
    try:
        if not ss["invoice_records"]:
            rows = sb.table("invoices").select("*").order("ym", desc=True).execute().data or []
            ss["invoice_records"] = [{
                "id": r.get("id"),
                "ym": r.get("ym"),
                "teamMemberId": r.get("team_member_id"),
                "locationId":   r.get("location_id"),
                "insType":      r.get("ins_type",""),
                "issueAmount":  float(r.get("issue_amount", 0)),
                "taxAmount":    float(r.get("tax_amount", 0)),
                "createdAt":    r.get("created_at"),
            } for r in rows]
    except Exception:
        pass

_prime_from_db()

# ============================
# 헤더
# ============================
st.title("팀 수입 관리")
if sb:
    st.success("✅ Supabase 연결됨 (팀 공동 사용 가능)")
else:
    st.info("🧪 Supabase 미설정 — 세션 메모리로 동작합니다. (Settings→Secrets에 SUPABASE 설정 시 팀 공유)")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["입력", "통계", "설정", "기록 관리", "정산", "계산서"])

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
# Tab 2: 통계 (수입 + 계산서)
# ============================
with tab2:
    def render_tab2():
        import pandas as pd

        st.markdown("### 통계")

        # ── 계산서 세션 최신화(연간 기준)
        try:
            reload_invoice_records(NOW_KST.year)
        except Exception:
            pass

        # ── 공용 이름 매핑
        team_members = st.session_state.get("team_members", []) or []
        locations    = st.session_state.get("locations", []) or []
        _mid2name = {m.get("id"): m.get("name") for m in team_members}
        _lid2name = {l.get("id"): l.get("name") for l in locations}

        # ─────────────────────────────────────────────────────────
        # (A) 수입 통계용 원천 DF (income_records → df)
        # ─────────────────────────────────────────────────────────
        income_records = st.session_state.get("income_records", []) or []
        if income_records:
            df = pd.DataFrame([{
                "date": r.get("date"),
                "amount": r.get("amount"),
                "member": _mid2name.get(r.get("teamMemberId"), ""),
                "location": _lid2name.get(r.get("locationId"), ""),
                "category": next((l.get("category") for l in locations if l.get("id") == r.get("locationId")), ""),
                "memo": r.get("memo", ""),
            } for r in income_records])
            # 정규화
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).copy()
            df["year"]  = df["date"].dt.year.astype(int)
            df["month"] = df["date"].dt.month.astype(int)
            df["day"]   = df["date"].dt.strftime("%Y-%m-%d")
        else:
            df = pd.DataFrame(columns=["date","amount","member","location","category","memo","year","month","day"])

        # 연도 선택(수입 통계용)
        years_income = sorted(df["year"].unique().tolist()) if not df.empty else [NOW_KST.year]
        default_y_income = NOW_KST.year if NOW_KST.year in years_income else years_income[-1]
        c1, c2 = st.columns([3,2])
        with c1:
            year_income = st.selectbox("연도(수입 통계)", years_income, index=years_income.index(default_y_income) if years_income else 0, key="t2_year_income")
        with c2:
            st.caption("선택 연도 외 데이터는 저장은 유지되며 열람만 가능합니다.")

        dfY = df[df["year"] == year_income].copy() if not df.empty else pd.DataFrame(columns=df.columns)

        # ─────────────────────────────────────────────────────────
        # (B) 하위 탭: 수입 통계(3개) + 계산서 통계(1개)
        # ─────────────────────────────────────────────────────────
        tab_mem, tab_loc_all, tab_loc_each, tab_invoice = st.tabs(
            ["팀원별 수입", "업체종합 수입", "업체개별 수입", "계산서 통계"]
        )

        # ───────── 1) 팀원별 수입 ─────────
        with tab_mem:
            st.markdown("#### 팀원별 수입 통계")
            if dfY.empty:
                st.info(f"{year_income}년 수입 데이터가 없습니다. (수입 입력 탭에서 추가)")
            else:
                members = sorted([m for m in dfY["member"].dropna().unique().tolist() if m])
                member_select = st.selectbox(
                    "팀원 선택(비교 모드 포함)",
                    ["팀원 비교(전체)"] + members,
                    index=0,
                    key="t2_mem_select"
                )

                if member_select == "팀원 비교(전체)":
                    annual_by_member = (
                        dfY.groupby("member", dropna=False)["amount"].sum()
                        .reset_index().rename(columns={"member":"팀원","amount":"연간 합계(만원)"})
                    )
                    if not annual_by_member.empty:
                        annual_by_member = annual_by_member.sort_values("연간 합계(만원)", ascending=False, kind="mergesort").reset_index(drop=True)
                        annual_by_member.insert(0, "순위", annual_by_member.index + 1)
                        st.markdown("##### 연간 합계")
                        st.dataframe(
                            annual_by_member[["순위","팀원","연간 합계(만원)"]],
                            use_container_width=True, hide_index=True,
                            column_config={"연간 합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                        )

                    months_avail_all = sorted(dfY["month"].unique().tolist())
                    if months_avail_all:
                        month_sel2 = st.selectbox("월 선택(보험/비보험 분리 보기)", months_avail_all, index=len(months_avail_all)-1, key="t2_mem_month_all")
                        df_month = dfY[dfY["month"] == month_sel2].copy()
                        by_mem_cat = df_month.groupby(["member","category"], dropna=False)["amount"].sum().reset_index()
                        pivot = by_mem_cat.pivot(index="member", columns="category", values="amount").fillna(0.0)
                        for col in ["보험","비보험"]:
                            if col not in pivot.columns:
                                pivot[col] = 0.0
                        pivot = pivot[["보험","비보험"]]
                        pivot["총합(만원)"] = pivot["보험"] + pivot["비보험"]
                        pivot = pivot.sort_values("총합(만원)", ascending=False).reset_index().rename(columns={"member":"팀원"})
                        st.markdown(f"##### {month_sel2}월 · 보험/비보험 분리 + 총합")
                        st.dataframe(
                            pivot[["팀원","총합(만원)","보험","비보험"]],
                            use_container_width=True, hide_index=True,
                            column_config={c: st.column_config.NumberColumn(format="%.0f") for c in ["총합(만원)","보험","비보험"]}
                        )
                    else:
                        st.info("해당 연도의 월 데이터가 없습니다.")

                else:
                    dfM_all = dfY[dfY["member"] == member_select].copy()
                    months_avail = sorted(dfM_all["month"].unique().tolist()) or list(range(1, 13))
                    month_sel = st.selectbox("월 선택(일별 상세/요약)", months_avail, index=(len(months_avail)-1 if months_avail else 0), key="t2_mem_month_single")

                    # 연간 요약
                    y_ins_amt = dfM_all.loc[dfM_all["category"]=="보험","amount"].sum()
                    y_non_amt = dfM_all.loc[dfM_all["category"]=="비보험","amount"].sum()
                    y_tot_amt = dfM_all["amount"].sum()
                    y_ins_cnt = int((dfM_all["category"]=="보험").sum())
                    y_non_cnt = int((dfM_all["category"]=="비보험").sum())
                    y_tot_cnt = int(len(dfM_all))

                    st.markdown("##### 연간 요약")
                    metric_cards([
                        ("연간 총합(만원)", f"{y_tot_amt:,.0f}"),
                        ("연간 보험(만원)", f"{y_ins_amt:,.0f}"),
                        ("연간 비보험(만원)", f"{y_non_amt:,.0f}"),
                        ("연간 건수(총합)", f"{y_tot_cnt:,}"),
                        ("연간 건수(보험)", f"{y_ins_cnt:,}"),
                        ("연간 건수(비보험)", f"{y_non_cnt:,}"),
                    ])

                    # 월간 요약
                    dfM_month = dfM_all[dfM_all["month"] == month_sel].copy()
                    m_ins_amt = dfM_month.loc[dfM_month["category"]=="보험","amount"].sum()
                    m_non_amt = dfM_month.loc[dfM_month["category"]=="비보험","amount"].sum()
                    m_tot_amt = dfM_month["amount"].sum()
                    m_ins_cnt = int((dfM_month["category"]=="보험").sum())
                    m_non_cnt = int((dfM_month["category"]=="비보험").sum())
                    m_tot_cnt = int(len(dfM_month))

                    st.markdown(f"##### {month_sel}월 요약")
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
                        dfM_all[dfM_all["month"] == month_sel]
                        .groupby("day", dropna=False)["amount"].sum().reset_index()
                        .rename(columns={"day":"날짜","amount":"금액(만원)"})
                        .sort_values("날짜")
                    )
                    st.markdown(f"##### {member_select} · {month_sel}월 일별 합계")
                    st.dataframe(
                        daily,
                        use_container_width=True, hide_index=True,
                        column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")}
                    )

                    # 상세 보기
                    days_in_month = sorted(dfM_all.loc[dfM_all["month"] == month_sel, "day"].dropna().unique().tolist())
                    if days_in_month:
                        sel_day = st.selectbox("상세 보기 날짜 선택", days_in_month, key="t2_member_day_detail")
                        details = dfM_all[(dfM_all["day"] == sel_day) & (dfM_all["month"] == month_sel)][
                            ["day","location","category","amount","memo"]
                        ].copy().rename(columns={"day":"날짜","location":"업체","category":"분류","amount":"금액(만원)","memo":"메모"})
                        st.markdown(f"##### {member_select} · {sel_day} 입력 내역")
                        st.dataframe(
                            details.sort_values(["업체","금액(만원)"], ascending=[True, False]),
                            use_container_width=True, hide_index=True,
                            column_config={"금액(만원)": st.column_config.NumberColumn(format="%.0f")}
                        )
                    else:
                        st.info("선택한 월에 입력된 데이터가 없어 상세 보기를 표시할 수 없습니다.")

        # ───────── 2) 업체종합 수입 ─────────
        with tab_loc_all:
            st.markdown("#### 업체종합 (보험/비보험 분리)")
            if dfY.empty:
                st.info(f"{year_income}년 수입 데이터가 없습니다.")
            else:
                cat_sel = st.radio("분류 선택", ["보험","비보험"], horizontal=True, key="t2_loc_all_cat")
                dfC = dfY[dfY["category"] == cat_sel].copy()

                if dfC.empty:
                    st.warning(f"{year_income}년 {cat_sel} 데이터가 없습니다.")
                else:
                    mode = st.radio("랭킹 모드", ["연간 순위","월간 순위"], horizontal=True, index=0, key="t2_loc_all_mode")

                    if mode == "연간 순위":
                        annual_loc = (
                            dfC.groupby("location", dropna=False)["amount"].sum().reset_index()
                            .rename(columns={"location":"업체","amount":"연간합계(만원)"})
                            .sort_values("연간합계(만원)", ascending=False).reset_index(drop=True)
                        )
                        annual_loc.insert(0, "순위", annual_loc.index + 1)
                        st.markdown(f"##### {cat_sel} · 업체별 연간 순위")
                        st.dataframe(
                            annual_loc[["순위","업체","연간합계(만원)"]],
                            use_container_width=True, hide_index=True,
                            column_config={"연간합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                        )
                    else:
                        months_avail_c = sorted(dfC["month"].unique().tolist())
                        if not months_avail_c:
                            st.info("선택 가능한 월이 없습니다.")
                        else:
                            month_rank = st.selectbox("월 선택(해당 월만 표시)", months_avail_c, index=len(months_avail_c)-1, key="t2_loc_all_month")
                            df_month = dfC[dfC["month"] == month_rank].copy()
                            monthly_loc = (
                                df_month.groupby("location", dropna=False)["amount"].sum().reset_index()
                                .rename(columns={"location":"업체","amount":"월합계(만원)"})
                                .sort_values("월합계(만원)", ascending=False).reset_index(drop=True)
                            )
                            monthly_loc.insert(0, "순위", monthly_loc.index + 1)
                            st.markdown(f"##### {cat_sel} · {month_rank}월 업체별 순위")
                            st.dataframe(
                                monthly_loc[["순위","업체","월합계(만원)"]],
                                use_container_width=True, hide_index=True,
                                column_config={"월합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                            )

        # ───────── 3) 업체개별 수입 ─────────
        with tab_loc_each:
            st.markdown("#### 업체개별 (선택 업체 × 팀원별 결과)")
            if dfY.empty:
                st.info(f"{year_income}년 수입 데이터가 없습니다.")
            else:
                cat_sel_e = st.radio("분류 선택", ["보험","비보험"], horizontal=True, key="t2_loc_each_cat")
                dfC_e = dfY[dfY["category"] == cat_sel_e].copy()
                if dfC_e.empty:
                    st.warning(f"{year_income}년 {cat_sel_e} 데이터가 없습니다.")
                else:
                    mode_e = st.radio("기준 선택", ["월간 순위","연간 순위"], horizontal=True, index=0, key="t2_loc_each_mode")

                    # 우선순위 예시 및 원본 순서
                    priority = ["부산숨", "성모안과", "아미유외과", "이진용외과"]
                    base_order = [x.get("name") for x in locations if x.get("name")]
                    present = set(dfC_e["location"].dropna().tolist())
                    ordered_filtered = [name for name in base_order if name in present]
                    loc_opts_e = [n for n in priority if n in ordered_filtered] + [n for n in ordered_filtered if n not in priority]

                    if not loc_opts_e:
                        st.info("선택 가능한 업체가 없습니다.")
                    else:
                        sel_loc_e = st.selectbox("업체 선택", loc_opts_e, index=0, key="t2_loc_each_loc")
                        dfS_e = dfC_e[dfC_e["location"] == sel_loc_e].copy()

                        def _df_with_total(df_in: pd.DataFrame, amount_col: str, name_col: str = "팀원") -> pd.DataFrame:
                            total = pd.DataFrame([{name_col: "총합", amount_col: df_in[amount_col].sum()}])
                            out = pd.concat([df_in, total], ignore_index=True)
                            return out

                        if mode_e == "월간 순위":
                            months_avail_e = sorted(dfS_e["month"].dropna().unique().tolist())
                            if not months_avail_e:
                                st.info("선택된 업체에 해당하는 월 데이터가 없습니다.")
                            else:
                                month_sel_e = st.selectbox("월 선택", months_avail_e, index=len(months_avail_e)-1, key="t2_loc_each_month")
                                st.markdown(f"**선택된 업체:** {sel_loc_e}  \n**조건:** {cat_sel_e} · {month_sel_e}월 기준")

                                dfM_e = dfS_e[dfS_e["month"] == month_sel_e].copy()
                                by_member_month_e = (
                                    dfM_e.groupby("member", dropna=False)["amount"].sum().reset_index()
                                    .rename(columns={"member":"팀원","amount":"월합계(만원)"})
                                    .sort_values("월합계(만원)", ascending=False).reset_index(drop=True)
                                )
                                by_member_month_e = _df_with_total(by_member_month_e, "월합계(만원)")
                                st.dataframe(
                                    by_member_month_e,
                                    use_container_width=True, hide_index=True,
                                    column_config={"월합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                                )

                                st.markdown("##### 참고: 팀원별 연간 합계")
                                by_member_year_e = (
                                    dfS_e.groupby("member", dropna=False)["amount"].sum().reset_index()
                                    .rename(columns={"member":"팀원","amount":"연간합계(만원)"})
                                    .sort_values("연간합계(만원)", ascending=False).reset_index(drop=True)
                                )
                                by_member_year_e = _df_with_total(by_member_year_e, "연간합계(만원)")
                                st.dataframe(
                                    by_member_year_e,
                                    use_container_width=True, hide_index=True,
                                    column_config={"연간합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                                )
                        else:
                            st.markdown(f"**선택된 업체:** {sel_loc_e}  \n**조건:** {cat_sel_e} · 연간 기준")
                            by_member_year_e = (
                                dfS_e.groupby("member", dropna=False)["amount"].sum().reset_index()
                                .rename(columns={"member":"팀원","amount":"연간합계(만원)"})
                                .sort_values("연간합계(만원)", ascending=False).reset_index(drop=True)
                            )
                            by_member_year_e = _df_with_total(by_member_year_e, "연간합계(만원)")
                            st.dataframe(
                                by_member_year_e,
                                use_container_width=True, hide_index=True,
                                column_config={"연간합계(만원)": st.column_config.NumberColumn(format="%.0f")}
                            )

        # ───────── 4) 계산서 통계 (발행금액 내림차순 정렬) ─────────
        with tab_invoice:
            st.markdown("#### 계산서 통계")

            inv = st.session_state.get("invoice_records", []) or []

            # 이름 매핑 (표시용)
            mmap = {m.get("id"): m.get("name") for m in (st.session_state.get("team_members",[]) or [])}
            lmap = {l.get("id"): l.get("name") for l in (st.session_state.get("locations",[])   or [])}

            # 드롭다운(팀원) — 팀 전체 + 모든 팀원(계산서가 없어도 표시는 가능)
            all_member_names = [m.get("name") for m in (st.session_state.get("team_members",[]) or []) if m.get("name")]
            mem = st.selectbox("팀원 선택", ["팀 전체"] + all_member_names, index=0, key="t2_inv_mem")

            # 연도 선택(계산서)
            years_avail = sorted({int(x["ym"].split("-")[0]) for x in inv if isinstance(x.get("ym"), str)} | {NOW_KST.year})
            y = st.selectbox("연도 선택", years_avail, index=years_avail.index(NOW_KST.year) if NOW_KST.year in years_avail else len(years_avail)-1, key="t2_inv_year")

            # 연간/월간
            period = st.radio("기간 선택", ["연간", "월간"], horizontal=True, index=0, key="t2_inv_period")

            # 보조 파서
            def _ym_year(s):
                try: return int(str(s).split("-")[0])
                except: return None
            def _ym_month(s):
                try: return int(str(s).split("-")[1])
                except: return None

            # 선택 연도 필터
            Q = [r for r in inv if _ym_year(r.get("ym")) == y]

            # 월간 모드면 월 선택
            months_avail = sorted({ _ym_month(r.get("ym")) for r in Q if _ym_month(r.get("ym")) })
            if period == "월간" and months_avail:
                m = st.selectbox("월", months_avail, index=len(months_avail)-1, key="t2_inv_month")
                Q = [r for r in Q if _ym_month(r.get("ym")) == m]
                titleP = f"{y}년 {m}월"
            else:
                titleP = f"{y}년"

            # 개인 선택 시 개인만 필터
            if mem != "팀 전체":
                name_to_id = {m.get("name"): m.get("id") for m in (st.session_state.get("team_members",[]) or [])}
                mem_id = name_to_id.get(mem)
                Q = [r for r in Q if r.get("teamMemberId") == mem_id]

            # 합계 지표
            tot_issue = sum(float(r.get("issueAmount") or 0) for r in Q)
            tot_tax   = sum(float(r.get("taxAmount") or 0) for r in Q)
            ratio_all = (tot_tax / tot_issue * 100.0) if tot_issue else 0.0

            c1,c2,c3 = st.columns(3)
            c1.metric(f"{titleP} 발행금액 총합(만원)", f"{tot_issue:,.0f}")
            c2.metric(f"{titleP} 세준금 총합(만원)",   f"{tot_tax:,.0f}")
            c3.metric("세준금 비율(%)",                f"{ratio_all:.2f}%")

            # 팀 전체일 경우: 팀원별 누적 표
            if mem == "팀 전체":
                st.markdown("##### 팀원별 누적 (선택 기간 기준)")
                if not Q:
                    st.info(f"{titleP} 팀원별 누적 데이터가 없습니다.")
                else:
                    agg = {}
                    for r in Q:
                        name = mmap.get(r.get("teamMemberId")) or "(이름없음)"
                        agg.setdefault(name, {"issue":0.0,"tax":0.0})
                        agg[name]["issue"] += float(r.get("issueAmount") or 0)
                        agg[name]["tax"]   += float(r.get("taxAmount") or 0)
                    rows = []
                    for name, v in agg.items():
                        rows.append({
                            "팀원": name,
                            "발행금액(만원)": v["issue"],
                            "세준금(만원)":   v["tax"],
                            "세준금비율(%)":  (v["tax"]/v["issue"]*100.0) if v["issue"] else 0.0
                        })
                    df_mem = pd.DataFrame(rows)
                    if not df_mem.empty:
                        df_mem = df_mem.sort_values("발행금액(만원)", ascending=False).reset_index(drop=True)
                        st.dataframe(
                            df_mem,
                            use_container_width=True, hide_index=True, key="t2_inv_by_member",
                            column_config={
                                "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                                "세준금(만원)":   st.column_config.NumberColumn(format="%.0f"),
                                "세준금비율(%)":  st.column_config.NumberColumn(format="%.2f"),
                            }
                        )

            # 업체별 목록 (발행금액 기준 내림차순)
            st.markdown("##### 업체별 계산서 목록")
            if not Q:
                st.info(f"{titleP} 조건에 맞는 계산서 데이터가 없습니다.")
            else:
                loc_agg = {}
                for r in Q:
                    loc = lmap.get(r.get("locationId")) or "(업체없음)"
                    d = loc_agg.setdefault(loc, {"issue":0.0,"tax":0.0})
                    d["issue"] += float(r.get("issueAmount") or 0)
                    d["tax"]   += float(r.get("taxAmount") or 0)
                rows = []
                for loc, v in loc_agg.items():
                    rows.append({
                        "업체명": loc,
                        "발행금액(만원)": v["issue"],
                        "세준금(만원)":   v["tax"],
                        "세준금비율(%)":  (v["tax"]/v["issue"]*100.0) if v["issue"] else 0.0
                    })
                df_loc = pd.DataFrame(rows)
                if not df_loc.empty:
                    df_loc = df_loc.sort_values("발행금액(만원)", ascending=False).reset_index(drop=True)
                    st.dataframe(
                        df_loc,
                        use_container_width=True, hide_index=True, key="t2_inv_by_loc",
                        column_config={
                            "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                            "세준금(만원)":   st.column_config.NumberColumn(format="%.0f"),
                            "세준금비율(%)":  st.column_config.NumberColumn(format="%.2f"),
                        }
                    )

    # 탭 보호: 다른 탭 노출 막지 않기
    try:
        render_tab2()
    except Exception as e:
        st.error(f"⚠️ 통계 탭 렌더링 오류: {e}")
        import traceback
        st.code(traceback.format_exc())





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
# Tab 5: 정산 (최종본 / 보험·비보험 규칙 포함)
# ============================
with tab5:
    st.markdown("### 정산")

    # ───────── 렌더링 보정 (웨일 대응) ─────────
    st.markdown("""
    <style>
    details > summary { line-height:1.5!important;white-space:normal!important;}
    .streamlit-expanderHeader p{line-height:1.5!important;white-space:normal!important;word-break:keep-all;overflow-wrap:anywhere;}
    </style>
    """, unsafe_allow_html=True)

    # ───────── Supabase 연결 ─────────
    from supabase import create_client
    import postgrest
    from datetime import datetime, timezone
    import pandas as pd
    import unicodedata, re

    SUPA_URL  = st.secrets["SUPABASE_URL"]
    SUPA_KEY  = st.secrets["SUPABASE_ANON_KEY"]
    sb = create_client(SUPA_URL, SUPA_KEY)
    sdb = sb.schema("public")

    # ───────── 유틸 ─────────
    def _name_from(_id, coll):
        for x in (coll or []):
            if x.get("id") == _id:
                return x.get("name", "")
        return ""

    def _members():
        return [x.get("name") for x in (st.session_state.team_members or []) if x.get("name")]

    def _grp(df):
        if df.empty:
            return pd.DataFrame(columns=["member","amount"])
        return df.groupby("member", as_index=False)["amount"].sum()

    def _norm_text(x: str) -> str:
        s = unicodedata.normalize("NFKC", str(x or ""))
        # 제로폭(Cf) 제거 + 모든 공백 제거
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
        s = re.sub(r"\s+", "", s)
        return s

    def _same_person(a, b) -> bool:
        return _norm_text(a) == _norm_text(b)

    def _is_insurance_category(cat) -> bool:
        """
        '보험'만 포함하고 '비보험'이 들어간 건 제외.
        DB 카테고리 명이 달라도 이 규칙이면 자동 필터됨.
        """
        s = _norm_text(cat).lower()
        return ("보험" in s) and ("비보험" not in s)

    def sb_get_month(ym_key):
        try:
            res = sdb.table("settlement_month").select("*").eq("ym_key", ym_key).limit(1).execute()
            data = getattr(res, "data", None) or []
            return data[0] if data else None
        except Exception as e:
            st.warning(f"월 설정 조회 실패: {e}")
            return None

    def sb_upsert_month(ym_key, sungmo_fixed, recv_bs, recv_am):
        payload = {
            "ym_key": ym_key,
            "sungmo_fixed": int(sungmo_fixed),
            "receiver_busansoom": recv_bs,
            "receiver_amiyou": recv_am,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        sdb.table("settlement_month").upsert(payload, on_conflict="ym_key").execute()

    def sb_list(name, ym_key):
        res = sdb.table(name).select("*").eq("ym_key", ym_key).order("created_at", desc=False).execute()
        return getattr(res, "data", None) or []

    def sb_add(name, payload): sdb.table(name).insert(payload).execute()
    def sb_update(name, pid, payload): sdb.table(name).update(payload).eq("id", pid).execute()
    def sb_delete(name, pid): sdb.table(name).delete().eq("id", pid).execute()

    # ───────── 원천 수입 ─────────
    rec = st.session_state.get("income_records", [])
    if not rec:
        st.info("수입 데이터가 없습니다. [수입 입력] 탭에서 먼저 추가해주세요.")
        st.stop()

    df = pd.DataFrame([{
        "date": r.get("date"),
        "amount": pd.to_numeric(r.get("amount"), errors="coerce"),
        "member": _name_from(r.get("teamMemberId",""), st.session_state.team_members),
        "location": _name_from(r.get("locationId",""), st.session_state.locations),
        "category": next((l.get("category") for l in (st.session_state.locations or []) if l.get("id")==r.get("locationId")), ""),
        "memo": r.get("memo",""),
    } for r in rec])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["year"]  = df["date"].dt.year.astype(int)
    df["month"] = df["date"].dt.month.astype(int)
    df["day"]   = df["date"].dt.strftime("%Y-%m-%d")

    members_all = _members()

    # ───────── 연/월 선택 ─────────
    cur_year = NOW_KST.year
    years = sorted(df["year"].unique().tolist())
    year = st.selectbox("정산 연도", years, index=years.index(cur_year) if cur_year in years else 0, key="settle_year")
    months = sorted(df[df["year"]==year]["month"].unique().tolist())
    month = st.selectbox("정산 월", months, index=len(months)-1, key="settle_month")
    ym_key = f"{year}-{month:02d}"

    # ───────── 월 설정 ─────────
    mrow = sb_get_month(ym_key)
    if not mrow:
        bs = members_all[0] if members_all else ""
        am = members_all[0] if members_all else ""
        sb_upsert_month(ym_key, 650, bs, am)  # 기본 650
        mrow = sb_get_month(ym_key)
    sungmo_fixed = int(mrow["sungmo_fixed"])
    recv_bs = mrow["receiver_busansoom"]   # 부산숨 수령자(허브)
    recv_am = mrow["receiver_amiyou"]      # 아미유 수령자
    recv_lee = "강현석"                    # 성모/이진용 수령자(고정) — 필요 시 DB화 가능

    tab_in, tab_out = st.tabs(["입력", "정산"])

    # ==================== 입력 ====================
    with tab_in:
        st.markdown("#### 월별 입력")

        # 기본 설정
        with st.expander("기본 설정", expanded=True):
            c1,c2,c3 = st.columns(3)
            nf = c1.number_input("성모 고정액(만원)", value=sungmo_fixed, step=10, key="settle_fixed")
            nb = c2.selectbox("부산숨 수령자", members_all, index=members_all.index(recv_bs), key="settle_bs_recv")
            na = c3.selectbox("아미유 수령자", members_all, index=members_all.index(recv_am), key="settle_am_recv")
            if st.button("저장", type="primary", key="save_month_conf"):
                sb_upsert_month(ym_key, nf, nb, na)
                st.success("저장되었습니다."); st.rerun()
            st.caption("이진용외과 수령자: 강현석 (고정)")

        # 팀비 입력
        with st.expander("팀비 사용 입력", expanded=True):
            c1,c2,c3 = st.columns([1,1,2])
            w = c1.selectbox("사용자", members_all, key="teamfee_user")
            a = c2.text_input("금액(만원)", "", key="teamfee_amount")
            m = c3.text_input("메모", "", key="teamfee_memo")
            if st.button("팀비 사용 추가", type="primary", key="teamfee_add_btn"):
                if a.strip().isdigit():
                    sb_add("settlement_teamfee", {"ym_key": ym_key, "who": w, "amount": int(a), "memo": m})
                    st.rerun()
                else:
                    st.error("금액은 숫자로 입력해주세요.")

        st.markdown("##### 팀비 사용 내역")
        tf = sb_list("settlement_teamfee", ym_key)
        if not tf:
            st.caption("아직 팀비 사용 내역이 없습니다.")
        else:
            for r in tf:
                c1,c2,c3,c4,c5 = st.columns([1,1,2,1,1])
                c1.write(r["who"]); c2.write(f"{r['amount']}만원"); c3.write(r["memo"])
                if c4.button("수정", key=f"tf_edit_{r['id']}"):
                    new_a = st.text_input("금액", str(r["amount"]), key=f"tf_na_{r['id']}")
                    new_m = st.text_input("메모", r["memo"], key=f"tf_nm_{r['id']}")
                    if st.button("저장", key=f"tf_save_{r['id']}"):
                        sb_update("settlement_teamfee", r["id"], {"amount": int(new_a), "memo": new_m})
                        st.rerun()
                if c5.button("삭제", key=f"tf_del_{r['id']}"):
                    sb_delete("settlement_teamfee", r["id"]); st.rerun()

        # 팀원 간 이체 입력
        with st.expander("팀원 간 이체 입력", expanded=True):
            c1,c2,c3,c4 = st.columns([1,1,1,2])
            f = c1.selectbox("보낸 사람", members_all, key="transfer_from")
            t = c2.selectbox("받는 사람", [x for x in members_all if x!=f], key="transfer_to")
            a = c3.text_input("금액(만원)", "", key="transfer_amount")
            m = c4.text_input("메모", "", key="transfer_memo")
            if st.button("이체 추가", type="primary", key="transfer_add_btn"):
                if a.strip().isdigit():
                    sb_add("settlement_transfer", {"ym_key": ym_key, "from": f, "to": t, "amount": int(a), "memo": m})
                    st.rerun()
                else:
                    st.error("금액은 숫자로 입력해주세요.")

        st.markdown("##### 이체 내역")
        tr = sb_list("settlement_transfer", ym_key)
        if not tr:
            st.caption("등록된 이체 내역이 없습니다.")
        else:
            for r in tr:
                c1,c2,c3,c4,c5 = st.columns([1,0.3,1,2,1])
                c1.write(r["from"]); c2.write("→"); c3.write(r["to"]); c4.write(r["memo"]); c5.write(f"{r['amount']}만원")
                if c5.button("삭제", key=f"tr_del_{r['id']}"):
                    sb_delete("settlement_transfer", r["id"]); st.rerun()

    # ==================== 정산 ====================
    with tab_out:
        st.markdown("#### 정산 결과")
        dfM = df[(df["year"]==year) & (df["month"]==month)]

        def locdf(n):
            d = dfM[dfM["location"]==n]
            if d.empty:
                return pd.DataFrame(columns=["member","amount"])
            return d.groupby("member", as_index=False)["amount"].sum()

        # 위치명(데이터 표기에 맞게 필요시 확장)
        bs_name  = next((x for x in dfM["location"].unique() if "숨"   in str(x)), "부산숨")
        sm_name  = next((x for x in dfM["location"].unique() if "성모" in str(x)), "성모안과")
        amy_name = next((x for x in dfM["location"].unique() if "아미유" in str(x)), "아미유외과")
        lee_name = next((x for x in dfM["location"].unique() if "이진용" in str(x)), "이진용외과")

        # 지점별 집계
        ib = locdf(bs_name)
        im = locdf(sm_name)
        il = locdf(lee_name)

        # ✅ 아미유: '보험'만 포함, '비보험' 포함된 건 제외
        amy_rows = dfM[dfM["location"].astype(str).str.contains("아미유", na=False)].copy()
        if not amy_rows.empty:
            amy_rows = amy_rows[ amy_rows["category"].apply(_is_insurance_category) ].copy()
            if not amy_rows.empty:
                ia = amy_rows.groupby("member", as_index=False)["amount"].sum()
            else:
                ia = pd.DataFrame(columns=["member","amount"])
        else:
            ia = pd.DataFrame(columns=["member","amount"])

        tf = sb_list("settlement_teamfee", ym_key)
        tr = sb_list("settlement_transfer", ym_key)

        # ───────── 트랜잭션 원장 ─────────
        tx = []

        # ① 성모 고정액(외부 유입) → 강현석 (순액 계산에서 제외, 원장에만 기록)
        if sungmo_fixed:
            tx.append({"from":"외부","to":recv_lee,"amount":int(sungmo_fixed),"reason":"성모 고정 수입"})

        # ② 부산숨: 수령자 → 팀원 (자기지급 제외)
        if recv_bs and not ib.empty:
            for _, r in ib.iterrows():
                m, a = r["member"], int(r["amount"])
                if m and a and not _same_person(m, recv_bs):
                    tx.append({"from":recv_bs,"to":m,"amount":a,"reason":bs_name})

        # ③ 성모: 강현석 → 팀원 (자기지급 제외)
        if not im.empty:
            for _, r in im.iterrows():
                m, a = r["member"], int(r["amount"])
                if m and a and not _same_person(m, recv_lee):
                    tx.append({"from":recv_lee,"to":m,"amount":a,"reason":sm_name})

        # ④ 이진용: 강현석 → 팀원 (자기지급 제외)
        if not il.empty:
            for _, r in il.iterrows():
                m, a = r["member"], int(r["amount"])
                if m and a and not _same_person(m, recv_lee):
                    tx.append({"from":recv_lee,"to":m,"amount":a,"reason":lee_name})

        # ⑤ 아미유(보험만 집계됨): 수령자 → 팀원 (자기지급 제외)
        if recv_am and not ia.empty:
            for _, r in ia.iterrows():
                m, a = r["member"], int(r["amount"])
                if m and a and not _same_person(m, recv_am):
                    tx.append({"from":recv_am,"to":m,"amount":a,"reason":amy_name})

        # ⑥ 팀원 간 이체
        for r in tr:
            amt = int(r.get("amount", 0) or 0)
            if amt:
                tx.append({"from":r["from"],"to":r["to"],"amount":amt,"reason":f"이체:{r.get('memo','')}"})

        # ⑦ 팀비 지출: 강현석 → 사용자
        for x in tf:
            amt = int(x.get("amount", 0) or 0)
            who = x.get("who", "")
            if who and amt:
                tx.append({"from":recv_lee,"to":who,"amount":amt,"reason":f"팀비:{x.get('memo','')}"})

        # ───────── 팀비 잔액 (별도 표기) ─────────
        sm_sum = int(im["amount"].sum()) if not im.empty else 0
        tf_sum = sum(int(x.get("amount", 0) or 0) for x in tf)
        teamfee_bal = int(sungmo_fixed) - sm_sum - tf_sum

        if not tx:
            st.info("정산할 항목이 없습니다."); st.stop()

        # ───────── 개인 순액 계산 (‘외부’ 제외) ─────────
        tx_df = pd.DataFrame(tx)
        tx_df = tx_df[tx_df["from"] != "외부"].copy()  # 외부→강 650 제외

        people = sorted(set(tx_df["from"]) | set(tx_df["to"]))
        bal = {p: 0 for p in people}
        for _, r in tx_df.iterrows():
            f, t, a = r["from"], r["to"], int(r["amount"])
            bal[f] -= a
            bal[t] += a

        # 실제 순액 표
        net = pd.DataFrame([{"사람": k, "순액(만원)": v} for k, v in bal.items()]).sort_values("순액(만원)", ascending=False)

        # 표시용 보정: 성모 수령자(현재 강현석) 표기에서 팀비잔액 분리 (예: 575 - 320 = 255)
        net_display = net.copy()
        if (net_display["사람"] == recv_lee).any():
            net_display.loc[net_display["사람"] == recv_lee, "순액(만원)"] = \
                net_display.loc[net_display["사람"] == recv_lee, "순액(만원)"].astype(int) - int(teamfee_bal)

        st.dataframe(net_display, use_container_width=True, hide_index=True)

        # ───────── 최종 지급 지시서 (허브=부산숨 수령자) ─────────
        st.markdown("##### 최종 지급 지시서 (개인 정산)")
        hub = recv_bs
        orders = []
        for _, r in net_display.iterrows():  # 화면 표시 기준으로 지시서 생성
            p, b = r["사람"], int(r["순액(만원)"])
            if _same_person(p, hub):
                continue
            if b > 0:
                orders.append({"From": hub, "To": p, "금액(만원)": b})
            elif b < 0:
                orders.append({"From": p, "To": hub, "금액(만원)": abs(b)})
        st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True)

        # ───────── 팀비 (별도) ─────────
        st.markdown(f"##### 팀비 (별도) — 잔액 {teamfee_bal}만원")
        st.caption(f"{sm_name}: 고정액 {sungmo_fixed} - 성모 지급합계 {sm_sum} - 팀비 사용합계 {tf_sum}")

        # 성모 지급 요약(개인별)
        st.markdown("###### 성모안과 지급 요약")
        if not im.empty:
            sm_view = im.rename(columns={"member":"수취자","amount":"금액(만원)"}).sort_values("금액(만원)", ascending=False)
            st.dataframe(sm_view, use_container_width=True, hide_index=True)
            st.caption(f"성모 지급합계: {int(sm_view['금액(만원)'].sum())}만원")
        else:
            st.caption("이번 달 성모안과 지급이 없습니다.")

        # 팀비 사용 내역
        st.markdown("###### 팀비 사용 내역")
        if tf:
            tf_df = pd.DataFrame(tf).copy()
            tf_df["amount"] = pd.to_numeric(tf_df["amount"], errors="coerce").fillna(0).astype(int)
            cols = ["who","amount","memo"]
            if "created_at" in tf_df.columns:
                try:
                    tf_df["일시"] = pd.to_datetime(tf_df["created_at"], errors="coerce")\
                                       .dt.tz_convert("Asia/Seoul")\
                                       .dt.strftime("%Y-%m-%d %H:%M")
                    cols = ["일시"] + cols
                except Exception:
                    pass
            view = tf_df[[c for c in cols if c in tf_df.columns]]\
                     .rename(columns={"who":"사용자","amount":"금액(만원)","memo":"메모"})
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.caption(f"팀비 사용합계: {int(tf_df['amount'].sum())}만원")
        else:
            st.caption("이번 달 팀비 사용 내역이 없습니다.")

# ============================
# Tab 6: 계산서 (입력 / 수정·삭제) — 완전 Supabase 연동형
# ============================
with tab6:
    import pandas as pd
    from datetime import datetime

    # 한국시간
    try:
        NOW_KST
    except NameError:
        NOW_KST = datetime.now()

    # 진입 시 최신 데이터 로드
    try:
        reload_invoice_records(None)
    except Exception as e:
        st.warning(f"계산서 데이터 로드 실패: {e}")

    # 안전 rerun
    def _inv_safe_rerun():
        try:
            st.rerun()
        except AttributeError:
            try:
                st.experimental_rerun()
            except Exception:
                pass

    # 헬퍼
    def _name_from(_id: str, coll: list[dict]) -> str:
        for x in coll:
            if x.get("id") == _id:
                return x.get("name", "")
        return ""

    def _member_id_by_name(name: str) -> str | None:
        for m in st.session_state.get("team_members", []):
            if m.get("name") == name:
                return m.get("id")
        return None

    def _loc_id_by_name(name: str) -> str | None:
        for l in st.session_state.get("locations", []):
            if l.get("name") == name:
                return l.get("id")
        return None

    # 세션 기본값
    st.session_state.setdefault("invoice_records", [])
    st.session_state.setdefault("inv_page", 0)
    st.session_state.setdefault("edit_invoice_id", None)
    st.session_state.setdefault("confirm_delete_invoice_id", None)

    # 서브탭
    tab6_input, tab6_manage = st.tabs(["입력", "수정·삭제"])

    # ============================
    # (1) 입력
    # ============================
    with tab6_input:
        st.subheader("계산서 입력")

        # 연/월 선택
        years_in_db = {
            int(x["ym"].split("-")[0]) for x in st.session_state.get("invoice_records", []) if x.get("ym")
        }
        years_avail = sorted(years_in_db | {NOW_KST.year})
        months_avail = list(range(1, 13))

        col_y, col_m = st.columns(2)
        with col_y:
            in_year = st.selectbox("연도", years_avail, index=years_avail.index(NOW_KST.year), key="inv_in_year")
        with col_m:
            in_month = st.selectbox("월", months_avail, index=NOW_KST.month - 1, key="inv_in_month")
        ym = f"{in_year:04d}-{in_month:02d}"

        # 팀원 선택
        member_names = [m.get("name", "") for m in st.session_state.get("team_members", []) if m.get("name")]
        member_name = st.selectbox("팀원", member_names, key="inv_member") if member_names else None
        member_id = _member_id_by_name(member_name) if member_name else None

        # 구분 / 업체
        ins_type = st.radio("구분", ["보험", "비보험"], horizontal=True, index=0, key="inv_ins")
        loc_all = st.session_state.get("locations", [])
        loc_candidates = [l for l in loc_all if l.get("category") == ins_type] or loc_all
        loc_names = [l.get("name", "") for l in loc_candidates if l.get("name")]
        loc_name = st.selectbox("업체", loc_names, key="inv_loc") if loc_names else None
        loc_id = _loc_id_by_name(loc_name) if loc_name else None

        # 금액
        def _num(v):
            try:
                return float(str(v).replace(",", "").strip())
            except:
                return None

        col_issue, col_tax = st.columns(2)
        with col_issue:
            issue_raw = st.text_input("계산서 발행금액(만원)", "", placeholder="예: 120", key="inv_issue")
        with col_tax:
            tax_raw = st.text_input("세준금(만원)", "", placeholder="예: 12", key="inv_tax")

        issue_amount = _num(issue_raw)
        tax_amount = _num(tax_raw)

        # 제출 버튼
        if st.button("계산서 등록", type="primary", key="inv_submit"):
            if not (member_id and loc_id and ym and issue_amount is not None and tax_amount is not None):
                st.error("모든 필드를 올바르게 입력하세요.")
            else:
                payload = {
                    "ym": ym,
                    "teamMemberId": member_id,
                    "locationId": loc_id,
                    "insType": ins_type,
                    "issueAmount": float(issue_amount),
                    "taxAmount": float(tax_amount),
                }

                # ✅ DB 입력 시도
                try:
                    _id = invoice_insert(payload)
                    reload_invoice_records(None)
                    st.success(f"{ym} 계산서가 DB에 저장되었습니다 ✅")
                    _inv_safe_rerun()
                except Exception as e:
                    st.error(f"❌ Supabase 저장 실패: {e}")

    # ============================
    # (2) 수정·삭제
    # ============================
    with tab6_manage:
        st.subheader("계산서 수정/삭제")

        inv = st.session_state.get("invoice_records", [])
        if not inv:
            st.info("DB에 계산서 데이터가 없습니다. [입력] 탭에서 추가해 주세요.")
        else:
            df = pd.DataFrame([
                {
                    "id": r.get("id"),
                    "ym": r.get("ym", ""),
                    "year": int(r.get("ym", "0000-00")[:4]) if r.get("ym") else None,
                    "month": int(r.get("ym", "0000-00")[5:7]) if r.get("ym") else None,
                    "member_id": r.get("teamMemberId"),
                    "member": _name_from(r.get("teamMemberId"), st.session_state.get("team_members", [])),
                    "location_id": r.get("locationId"),
                    "location": _name_from(r.get("locationId"), st.session_state.get("locations", [])),
                    "ins_type": r.get("insType", ""),
                    "issue": float(r.get("issueAmount", 0) or 0.0),
                    "tax": float(r.get("taxAmount", 0) or 0.0),
                }
                for r in inv
            ])

            # 필터 UI
            years = sorted(df["year"].dropna().unique().tolist() + [NOW_KST.year])
            c1, c2, c3 = st.columns([2, 3, 2])
            with c1:
                year_sel = st.selectbox("연도", years, index=years.index(NOW_KST.year), key="inv_year_sel")
            with c2:
                months = sorted(df.loc[df["year"] == year_sel, "month"].dropna().unique().tolist())
                month_opts = ["전체"] + months
                month_sel = st.selectbox("월", month_opts, index=0, key="inv_month_sel")
            with c3:
                order_by = st.selectbox("정렬", ["발행금액↓", "발행금액↑", "세준금↓", "세준금↑"], key="inv_order_by")

            c4, c5, c6 = st.columns([2, 2, 2])
            with c4:
                mem_opts = ["전체"] + sorted([m.get("name", "") for m in st.session_state.get("team_members", [])])
                mem_sel = st.selectbox("팀원", mem_opts, index=0, key="inv_mem_sel")
            with c5:
                ins_sel = st.selectbox("구분", ["전체", "보험", "비보험"], index=0, key="inv_ins_sel")
            with c6:
                loc_pool = st.session_state.get("locations", [])
                if ins_sel != "전체":
                    loc_pool = [l for l in loc_pool if l.get("category") == ins_sel]
                loc_opts = ["전체"] + [l.get("name", "") for l in loc_pool]
                loc_sel = st.selectbox("업체", loc_opts, index=0, key="inv_loc_sel")

            q = df[df["year"] == year_sel].copy()
            if month_sel != "전체":
                q = q[q["month"] == month_sel]
            if mem_sel != "전체":
                q = q[q["member"] == mem_sel]
            if ins_sel != "전체":
                q = q[q["ins_type"] == ins_sel]
            if loc_sel != "전체":
                q = q[q["location"] == loc_sel]

            # 정렬
            sort_map = {
                "발행금액↓": ("issue", False),
                "발행금액↑": ("issue", True),
                "세준금↓": ("tax", False),
                "세준금↑": ("tax", True),
            }
            key, asc = sort_map[order_by]
            q = q.sort_values([key, "id"], ascending=[asc, True])

            # 페이지 표시
            PAGE_SIZE = 20
            total = len(q)
            total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
            st.session_state.inv_page = min(st.session_state.inv_page, total_pages - 1)
            st.session_state.inv_page = max(st.session_state.inv_page, 0)

            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc1:
                if st.button("⬅ 이전", disabled=(st.session_state.inv_page == 0), key="inv_prev"):
                    st.session_state.inv_page -= 1
                    _inv_safe_rerun()
            with pc2:
                st.markdown(
                    f"<div style='text-align:center'>페이지 {st.session_state.inv_page+1} / {total_pages} (총 {total}건)</div>",
                    unsafe_allow_html=True,
                )
            with pc3:
                if st.button("다음 ➡", disabled=(st.session_state.inv_page >= total_pages - 1), key="inv_next"):
                    st.session_state.inv_page += 1
                    _inv_safe_rerun()

            start = st.session_state.inv_page * PAGE_SIZE
            page_df = q.iloc[start : start + PAGE_SIZE].copy()

            st.dataframe(
                page_df[["ym", "member", "location", "ins_type", "issue", "tax"]].rename(
                    columns={
                        "ym": "연월",
                        "member": "팀원",
                        "location": "업체",
                        "ins_type": "구분",
                        "issue": "발행금액(만원)",
                        "tax": "세준금(만원)",
                    }
                ),
                use_container_width=True,
                column_config={
                    "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                    "세준금(만원)": st.column_config.NumberColumn(format="%.0f"),
                },
            )

            # 수정/삭제 버튼
            for _, row in page_df.iterrows():
                with st.container(border=True):
                    left, right = st.columns([6, 2])
                    left.write(
                        f"**{row['ym']} · {row['member']} · {row['location']} · {row['ins_type']}**  —  "
                        f"발행 {row['issue']:.0f}만원 / 세준 {row['tax']:.0f}만원"
                    )
                    with right:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("🖉 수정", key=f"edit_inv_{row['id']}"):
                                st.session_state.edit_invoice_id = row["id"]
                                _inv_safe_rerun()
                        with col_b:
                            if st.button("🗑 삭제", key=f"del_inv_{row['id']}"):
                                st.session_state.confirm_delete_invoice_id = row["id"]
                                _inv_safe_rerun()

            # 삭제 처리
            if st.session_state.confirm_delete_invoice_id:
                rid = st.session_state.confirm_delete_invoice_id
                with st.container(border=True):
                    st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 삭제 확정", key="inv_delete_confirm"):
                            try:
                                invoice_delete(rid)
                                reload_invoice_records(None)
                                st.success("삭제되었습니다 ✅")
                            except Exception as e:
                                st.error(f"❌ Supabase 삭제 실패: {e}")
                            st.session_state.confirm_delete_invoice_id = None
                            _inv_safe_rerun()
                    with c2:
                        if st.button("❌ 취소", key="inv_delete_cancel"):
                            st.session_state.confirm_delete_invoice_id = None
                            _inv_safe_rerun()

            # 수정 폼
            if st.session_state.edit_invoice_id:
                target = next(
                    (x for x in st.session_state.invoice_records if x.get("id") == st.session_state.edit_invoice_id),
                    None,
                )
                if target:
                    st.markdown("#### 선택한 계산서 수정")

                    cur_year = int(target["ym"][:4])
                    cur_month = int(target["ym"][5:7])
                    cur_member_name = _name_from(target["teamMemberId"], st.session_state.get("team_members", []))
                    cur_loc = next(
                        (l for l in st.session_state.get("locations", []) if l.get("id") == target.get("locationId")),
                        None,
                    )
                    cur_ins = target.get("insType", "보험")

                    c1, c2 = st.columns(2)
                    with c1:
                        years_all = sorted(
                            {int(x["ym"][:4]) for x in st.session_state.get("invoice_records", []) if x.get("ym")}
                            | {NOW_KST.year}
                        )
                        edit_year = st.selectbox("연도", years_all, index=years_all.index(cur_year), key="edit_inv_year")
                        edit_month = st.selectbox("월", list(range(1, 13)), index=cur_month - 1, key="edit_inv_month")

                        members = {m.get("name", ""): m.get("id") for m in st.session_state.get("team_members", [])}
                        mem_names = list(members.keys())
                        cur_idx = mem_names.index(cur_member_name) if cur_member_name in mem_names else 0
                        member_name_edit = st.selectbox("팀원", mem_names, index=cur_idx, key="edit_inv_member")
                        member_id_edit = members[member_name_edit]
                    with c2:
                        ins_edit = st.radio("구분", ["보험", "비보험"], index=0 if cur_ins == "보험" else 1, horizontal=True, key="edit_inv_ins")
                        locs = [l for l in st.session_state.get("locations", []) if l.get("category") == ins_edit]
                        loc_options = {l.get("name", ""): l.get("id") for l in locs}
                        names = list(loc_options.keys())
                        def_idx = names.index(cur_loc.get("name")) if cur_loc and cur_loc.get("name") in names else 0
                        loc_name_edit = st.selectbox("업체", names, index=def_idx, key="edit_inv_loc")
                        loc_id_edit = loc_options[loc_name_edit]

                    col1, col2 = st.columns(2)
                    with col1:
                        issue_raw = st.text_input("계산서 발행금액(만원)", value=str(int(target.get("issueAmount", 0))), key="edit_inv_issue")
                    with col2:
                        tax_raw = st.text_input("세준금(만원)", value=str(int(target.get("taxAmount", 0))), key="edit_inv_tax")
                    try:
                        issue_edit = float(str(issue_raw).replace(",", ""))
                        tax_edit = float(str(tax_raw).replace(",", ""))
                    except:
                        issue_edit, tax_edit = None, None
                        st.error("금액은 숫자만 입력하세요.")

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ 저장", type="primary", key="edit_inv_save"):
                            if issue_edit is None or tax_edit is None:
                                st.error("금액을 올바르게 입력하세요.")
                            else:
                                new_data = {
                                    "ym": f"{edit_year:04d}-{edit_month:02d}",
                                    "teamMemberId": member_id_edit,
                                    "locationId": loc_id_edit,
                                    "insType": ins_edit,
                                    "issueAmount": issue_edit,
                                    "taxAmount": tax_edit,
                                }
                                try:
                                    invoice_update(target["id"], new_data)
                                    reload_invoice_records(None)
                                    st.success("수정 완료 ✅")
                                except Exception as e:
                                    st.error(f"❌ Supabase 수정 실패: {e}")
                                st.session_state.edit_invoice_id = None
                                _inv_safe_rerun()
                    with b2:
                        if st.button("❌ 취소", key="edit_inv_cancel"):
                            st.session_state.edit_invoice_id = None
                            _inv_safe_rerun()
