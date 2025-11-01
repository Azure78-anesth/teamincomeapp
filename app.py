import os
from datetime import datetime
from typing import Any, Dict

import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Supabase (optional, graceful fallback to in-memory)
# ──────────────────────────────────────────────────────────────────────────────
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")
sb = None
try:
    if SB_URL and SB_KEY:
        from supabase import create_client
        sb = create_client(SB_URL, SB_KEY)
except Exception:
    sb = None

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="팀 수입 · 계산서 관리", layout="wide")

def _ensure_session_defaults():
    if "team_members" not in st.session_state:
        st.session_state.team_members = []
    if "locations" not in st.session_state:
        st.session_state.locations = []
    if "income_records" not in st.session_state:
        st.session_state.income_records = []
    if "invoice_records" not in st.session_state:
        st.session_state.invoice_records = []

def _load_members():
    if sb:
        try:
            rows = sb.table("team_members").select("*").order("name").execute().data
            return [{"id": r["id"], "name": r["name"]} for r in rows]
        except Exception:
            pass
    # fallback demo
    return st.session_state.get("team_members") or [
        {"id": "m1", "name": "홍길동"},
        {"id": "m2", "name": "김철수"},
        {"id": "m3", "name": "이영희"},
    ]

def _load_locations():
    if sb:
        try:
            rows = sb.table("locations").select("*").order("name").execute().data
            return [{"id": r["id"], "name": r["name"], "category": r.get("category", "")} for r in rows]
        except Exception:
            pass
    # fallback demo
    return st.session_state.get("locations") or [
        {"id": "l1", "name": "서울의원", "category": "보험"},
        {"id": "l2", "name": "부산클리닉", "category": "비보험"},
        {"id": "l3", "name": "인천의원", "category": "보험"},
    ]

def _load_incomes():
    if sb:
        try:
            rows = sb.table("incomes").select("*").order("date", desc=True).limit(2000).execute().data
            return [{
                "id": r["id"],
                "date": r["date"],
                "teamMemberId": r.get("team_member_id"),
                "locationId": r.get("location_id"),
                "amount": float(r.get("amount", 0) or 0),
                "memo": r.get("memo", ""),
            } for r in rows]
        except Exception:
            pass
    return st.session_state.get("income_records", [])

def _load_invoices():
    if sb:
        try:
            rows = sb.table("invoices").select("*").order("ym", desc=True).limit(5000).execute().data
            return [{
                "id": r["id"],
                "ym": r.get("ym"),  # 'YYYY-MM'
                "teamMemberId": r.get("team_member_id"),
                "locationId": r.get("location_id"),
                "insType": r.get("ins_type", ""),       # 보험/비보험
                "issueAmount": float(r.get("issue_amount", 0) or 0),
                "taxAmount": float(r.get("tax_amount", 0) or 0),  # 세준금
                "memo": r.get("memo", ""),
            } for r in rows]
        except Exception:
            pass
    return st.session_state.get("invoice_records", [])

def load_data():
    _ensure_session_defaults()
    st.session_state.team_members   = _load_members()
    st.session_state.locations      = _load_locations()
    st.session_state.income_records = _load_incomes()
    st.session_state.invoice_records= _load_invoices()

def upsert_row(table: str, payload: Dict[str, Any]):
    """공통 upsert (세션 캐시 반영 + 가능하면 DB insert)"""
    if table == "incomes":
        if sb:
            try:
                sb.table("incomes").insert({
                    "id": payload["id"],
                    "date": payload["date"],
                    "team_member_id": payload["teamMemberId"],
                    "location_id": payload["locationId"],
                    "amount": payload["amount"],
                    "memo": payload.get("memo", ""),
                }).execute()
            except Exception:
                st.warning("Supabase 저장 실패(오프라인/스키마 미확장). 임시 메모리에만 보관합니다.")
        st.session_state.income_records.append(payload)

    elif table == "invoices":
        if sb:
            try:
                sb.table("invoices").insert({
                    "id": payload["id"],
                    "ym": payload["ym"],
                    "team_member_id": payload["teamMemberId"],
                    "location_id": payload["locationId"],
                    "ins_type": payload["insType"],
                    "issue_amount": payload["issueAmount"],
                    "tax_amount": payload["taxAmount"],
                    "memo": payload.get("memo", ""),
                }).execute()
            except Exception:
                st.warning("Supabase 저장 실패(오프라인/스키마 미확장). 임시 메모리에만 보관합니다.")
        st.session_state.invoice_records.append(payload)

def update_invoice(id_value: str, payload: Dict[str, Any]):
    """계산서 단건 업데이트(편집 확장 대비)"""
    if sb:
        try:
            sb.table("invoices").update({
                "ym": payload["ym"],
                "team_member_id": payload["teamMemberId"],
                "location_id": payload["locationId"],
                "ins_type": payload["insType"],
                "issue_amount": payload["issueAmount"],
                "tax_amount": payload["taxAmount"],
                "memo": payload.get("memo", ""),
            }).eq("id", id_value).execute()
            load_data()
            return
        except Exception:
            st.warning("Supabase 업데이트 실패(오프라인?) → 임시 메모리에만 반영합니다.")
    for r in st.session_state.invoice_records:
        if r["id"] == id_value:
            r.update(payload)
            break

# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────
st.title("팀 수입 · 계산서 관리")
load_data()

# 탭 구성 (끝에 '계산서' 탭 포함)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["입력", "통계", "정산", "기록 관리", "기타", "계산서"])

# ──────────────────────────────────────────────────────────────────────────────
# Tab1: 수입 입력 (기본 유지)
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("수입 입력")
    d = st.date_input("날짜", value=datetime.today())
    member_names = [m["name"] for m in st.session_state.team_members]
    member_map   = {m["name"]: m["id"] for m in st.session_state.team_members}
    member_name  = st.selectbox("팀원", member_names) if member_names else None
    member_id    = member_map.get(member_name) if member_name else None

    loc_label = [l.get("name","") for l in st.session_state.locations]
    loc_pick  = st.selectbox("업체", loc_label) if loc_label else None
    loc_id    = None
    if loc_pick and st.session_state.locations:
        loc_idx = loc_label.index(loc_pick)
        loc_id  = st.session_state.locations[loc_idx]["id"]

    amount_raw = st.text_input("금액(만원 단위)", value="", placeholder="예: 50")
    try:
        amount = float(amount_raw.replace(",","").strip()) if amount_raw.strip() != "" else None
    except ValueError:
        amount = None
        st.error("금액은 숫자만 입력하세요. (예: 50)")

    memo_new = st.text_input("메모(선택)", value="", placeholder="비고를 적어주세요")

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
                "memo": memo_new.strip(),
            })
            st.success(f"{d.strftime('%Y-%m-%d')} 수입이 저장되었습니다 ✅")

# ──────────────────────────────────────────────────────────────────────────────
# Tab2: 통계 → 서브탭에 '계산서 통계' 추가
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    sub_tab1, sub_tab2 = st.tabs(["수입 통계", "계산서 통계"])

    # 기존 수입 통계는 이곳에 유지/추가
    with sub_tab1:
        st.info("기존 수입 통계 UI를 여기에 유지/구현하세요.")

    with sub_tab2:
        st.subheader("📊 계산서 통계")

        inv_records = st.session_state.get("invoice_records", [])
        if not inv_records:
            st.info("등록된 계산서 데이터가 없습니다.")
        else:
            df = pd.DataFrame([{
                "ym": r.get("ym", ""),
                "teamMemberId": r.get("teamMemberId"),
                "locationId": r.get("locationId"),
                "issue": float(r.get("issueAmount", 0) or 0),
                "tax": float(r.get("taxAmount", 0) or 0),
            } for r in inv_records])

            # 연/월 분리(방어 포함)
            try:
                df[["year", "month"]] = df["ym"].str.split("-", expand=True).astype(int)
            except Exception:
                df["year"]  = pd.to_numeric(df["ym"].str.slice(0, 4), errors="coerce").fillna(0).astype(int)
                df["month"] = pd.to_numeric(df["ym"].str.slice(5, 7), errors="coerce").fillna(0).astype(int)

            # 이름 매핑
            members = {m["id"]: m["name"] for m in st.session_state.get("team_members", [])}
            locs    = {l["id"]: l["name"] for l in st.session_state.get("locations", [])}
            df["member"]   = df["teamMemberId"].map(members)
            df["location"] = df["locationId"].map(locs)
            df["ratio"]    = df.apply(lambda r: (r["tax"]/r["issue"]*100) if r["issue"] else 0.0, axis=1)

            # ── 개인/팀 전체 통계
            st.markdown("### 👤 개인 및 팀 전체 통계")

            member_opts = ["팀 전체"] + sorted([x for x in df["member"].dropna().unique().tolist()])
            sel_member  = st.selectbox("팀원 선택", member_opts)

            years        = sorted([y for y in df["year"].unique() if y > 0])
            default_year = years[-1] if years else datetime.today().year
            sel_year     = st.selectbox("연도 선택", years if years else [default_year],
                                        index=(len(years)-1) if years else 0)

            months   = sorted(df.loc[df["year"] == sel_year, "month"].unique().tolist())
            sel_mode = st.radio("기간 선택", ["연간", "월간"], horizontal=True, index=0)

            if sel_mode == "월간" and months:
                sel_month   = st.selectbox("월 선택", months, index=len(months)-1)
                df_period   = df[(df["year"] == sel_year) & (df["month"] == sel_month)]
                title_range = f"{sel_year}년 {sel_month}월"
            else:
                df_period   = df[df["year"] == sel_year]
                title_range = f"{sel_year}년"

            if sel_member != "팀 전체":
                df_period = df_period[df_period["member"] == sel_member]

            total_issue = float(df_period["issue"].sum())
            total_tax   = float(df_period["tax"].sum())
            ratio_all   = (total_tax/total_issue*100) if total_issue else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric(f"{title_range} 발행금액 총합(만원)", f"{total_issue:,.0f}")
            c2.metric(f"{title_range} 세준금 총합(만원)",   f"{total_tax:,.0f}")
            c3.metric("세준금 비율(%)",                    f"{ratio_all:.2f}%")

            st.divider()

            # ── 업체별 통계: 정렬 기준 '발행금액 총합' 내림차순
            st.markdown("### 🏢 업체별 통계")

            agg_mode = st.radio("조회 모드", ["연간", "월간"], horizontal=True, index=0)
            if agg_mode == "월간" and months:
                msel   = st.selectbox("월 선택", months, index=len(months)-1)
                df_sel = df[(df["year"] == sel_year) & (df["month"] == msel)]
                title  = f"{sel_year}년 {msel}월 업체별"
            else:
                df_sel = df[df["year"] == sel_year]
                title  = f"{sel_year}년 업체별"

            grouped = (
                df_sel.groupby("location", as_index=False)
                .agg({"issue": "sum", "tax": "sum"})
            )
            grouped["ratio"] = grouped.apply(
                lambda r: (r["tax"]/r["issue"]*100) if r["issue"] else 0.0, axis=1
            )
            grouped = grouped.sort_values("issue", ascending=False)  # 발행금액 기준

            st.markdown(f"#### {title} 계산서 현황 (발행금액 기준)")
            st.dataframe(
                grouped.rename(
                    columns={
                        "location": "업체명",
                        "issue": "발행금액(만원)",
                        "tax": "세준금(만원)",
                        "ratio": "세준금비율(%)",
                    }
                )[["업체명", "발행금액(만원)", "세준금(만원)", "세준금비율(%)"]],
                use_container_width=True,
                column_config={
                    "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                    "세준금(만원)": st.column_config.NumberColumn(format="%.0f"),
                    "세준금비율(%)": st.column_config.NumberColumn(format="%.2f"),
                },
            )

# ──────────────────────────────────────────────────────────────────────────────
# Tab3: 정산 (placeholder)
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.info("정산 탭은 기존 내용을 유지하거나, 필요 시 추가 구현하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# Tab4: 기록 관리 (placeholder)
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.info("기록 관리 탭은 기존 내용을 유지하거나, 필요 시 추가 구현하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# Tab5: 기타 (placeholder)
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    st.info("기존 탭5 내용이 있다면 이 영역에 통합하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# Tab6: 계산서 (신규)
# ──────────────────────────────────────────────────────────────────────────────
with tab6:
    st.subheader("계산서 입력 · 월별 관리")

    month_pick = st.date_input("달 선택", value=datetime.today().replace(day=1))
    ym = f"{month_pick.year:04d}-{month_pick.month:02d}"

    member_names = [m["name"] for m in st.session_state.team_members]
    member_map   = {m["name"]: m["id"] for m in st.session_state.team_members}
    member_name  = st.selectbox("팀원", member_names) if member_names else None
    member_id    = member_map.get(member_name) if member_name else None

    ins_type = st.radio("구분", ["보험", "비보험"], horizontal=True, index=0)

    def _match_ins_type(loc):
        return (loc.get("category", "").strip() == ins_type)

    loc_opts = [l for l in st.session_state.locations if _match_ins_type(l)]
    if not loc_opts:
        loc_opts = st.session_state.locations

    loc_label = [f'{l.get("name","")} ({l.get("category","")})' for l in loc_opts]
    loc_pick  = st.selectbox("업체", loc_label) if loc_opts else None
    loc_id    = (loc_opts[loc_label.index(loc_pick)]["id"] if loc_pick else None) if loc_opts else None

    issue_raw = st.text_input("계산서 발행금액(만원)", value="", placeholder="예: 120")
    tax_raw   = st.text_input("세준금(만원)", value="", placeholder="예: 12")

    def _num(v):
        try: return float(str(v).replace(",", "").strip())
        except Exception: return None

    issue_amount = _num(issue_raw)
    tax_amount   = _num(tax_raw)

    memo_invoice = st.text_input("메모(선택)", value="", placeholder="비고를 적어주세요")

    if st.button("계산서 등록", type="primary"):
        if not (member_id and loc_id and ym and issue_amount is not None and tax_amount is not None and issue_amount >= 0 and tax_amount >= 0):
            st.error("모든 필드를 올바르게 입력하세요.")
        else:
            iid = f"inv_{datetime.utcnow().timestamp()}"
            payload = {
                "id": iid,
                "ym": ym,
                "teamMemberId": member_id,
                "locationId": loc_id,
                "insType": ins_type,             # 보험/비보험
                "issueAmount": float(issue_amount),
                "taxAmount": float(tax_amount),  # 세준금
                "memo": memo_invoice.strip(),
            }
            upsert_row("invoices", payload)
            st.success(f"{ym} 계산서가 저장되었습니다 ✅")

    st.divider()
    st.markdown("#### 월별 계산서 현황")

    inv_all = st.session_state.get("invoice_records", [])
    if inv_all:
        years_avail = sorted({int(x["ym"].split("-")[0]) for x in inv_all if x.get("ym")})
        months_avail = list(range(1, 13))
    else:
        years_avail = [datetime.today().year]
        months_avail = list(range(1, 13))

    qy = st.selectbox("연도", options=years_avail, index=years_avail.index(month_pick.year) if month_pick.year in years_avail else len(years_avail)-1)
    qm = st.selectbox("월", options=months_avail, index=month_pick.month-1)
    qym = f"{qy:04d}-{qm:02d}"

    rows = [r for r in inv_all if r.get("ym") == qym]
    df = pd.DataFrame([{
        "연월": r["ym"],
        "팀원": next((m["name"] for m in st.session_state.team_members if m["id"] == r["teamMemberId"]), ""),
        "업체": next((l["name"] for l in st.session_state.locations if l["id"] == r["locationId"]), ""),
        "구분": r.get("insType", ""),
        "발행금액(만원)": r.get("issueAmount", 0.0),
        "세준금(만원)": r.get("taxAmount", 0.0),
        "메모": r.get("memo", ""),
    } for r in rows])

    if not df.empty:
        st.dataframe(
            df[["연월", "팀원", "업체", "구분", "발행금액(만원)", "세준금(만원)", "메모"]],
            use_container_width=True,
            column_config={
                "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                "세준금(만원)": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        total_issue = float(df["발행금액(만원)"].sum())
        total_tax   = float(df["세준금(만원)"].sum())
        col_a, col_b = st.columns(2)
        col_a.metric(f"{qym} 발행금액 합계(만원)", f"{total_issue:,.0f}")
        col_b.metric(f"{qym} 세준금 합계(만원)", f"{total_tax:,.0f}")
    else:
        st.info(f"{qym}에 등록된 계산서가 없습니다.")
