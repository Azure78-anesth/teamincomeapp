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

# ─────────────────────────────────────────
# Invoices (계산서) – snake_case 테이블 전용  ← ① 추가 블록 시작
# ─────────────────────────────────────────
def load_invoices(year: int | None = None):
    """
    Supabase invoices → st.session_state.invoice_records 로딩
    (수입/팀원/업체 로직과 분리, incomes에는 영향 X)
    """
    st.session_state.setdefault("invoice_records", [])
    if not sb:
        return
    try:
        q = sb.table("invoices").select(
            "id, ym, team_member_id, location_id, ins_type, issue_amount, tax_amount, created_at"
        )
        if year:
            q = q.like("ym", f"{year}-%")
        try:
            q = q.order("ym", desc=True).order("created_at", desc=True)
        except Exception:
            pass
        res = q.execute()
        rows = res.data or []
        st.session_state.invoice_records = [{
            "id":           r.get("id"),
            "ym":           r.get("ym"),
            "teamMemberId": r.get("team_member_id"),
            "locationId":   r.get("location_id"),
            "insType":      r.get("ins_type", ""),
            "issueAmount":  float(r.get("issue_amount") or 0),
            "taxAmount":    float(r.get("tax_amount") or 0),
            "createdAt":    r.get("created_at"),
        } for r in rows]
    except Exception as e:
        st.warning(f"계산서 로드 실패: {e}")

def invoice_insert(payload: Dict[str, Any]) -> tuple[bool, str | None]:
    """
    payload:
      ym, teamMemberId, locationId, insType, issueAmount, taxAmount
    ※ incomes와 분리되어 있어 수입 입력(upsert_row)에는 영향 없음
    """
    st.session_state.setdefault("invoice_records", [])

    if not sb:
        # 오프라인/테스트: 세션에만 보관
        new_id = f"inv_{datetime.now().timestamp()}"
        st.session_state.invoice_records.append({
            "id": new_id, **payload, "createdAt": datetime.now().isoformat()
        })
        return (True, None)

    try:
        res = (
            sb.table("invoices")
              .insert({
                  "ym":             payload["ym"],
                  "team_member_id": payload["teamMemberId"],
                  "location_id":    payload["locationId"],
                  "ins_type":       payload.get("insType", ""),
                  "issue_amount":   float(payload.get("issueAmount", 0) or 0),
                  "tax_amount":     float(payload.get("taxAmount",   0) or 0),
              })
              .select("id")
              .execute()
        )
        if not res.data:
            return (False, "INSERT 응답이 비었습니다(RLS/권한/정책 문제 가능).")
        return (True, None)
    except Exception as e:
        return (False, f"계산서 INSERT 실패: {e}")

def invoice_update(id_value: str, payload: Dict[str, Any]) -> tuple[bool, str | None]:
    if not sb:
        for r in st.session_state.get("invoice_records", []):
            if r.get("id") == id_value:
                r.update(payload)
                break
        return (True, None)
    try:
        sb.table("invoices").update({
            "ym":             payload["ym"],
            "team_member_id": payload["teamMemberId"],
            "location_id":    payload["locationId"],
            "ins_type":       payload.get("insType", ""),
            "issue_amount":   float(payload.get("issueAmount", 0) or 0),
            "tax_amount":     float(payload.get("taxAmount",   0) or 0),
        }).eq("id", id_value).execute()
        return (True, None)
    except Exception as e:
        return (False, f"계산서 UPDATE 실패: {e}")

def invoice_delete(id_value: str) -> tuple[bool, str | None]:
    if not sb:
        st.session_state["invoice_records"] = [
            r for r in st.session_state.get("invoice_records", []) if r.get("id") != id_value
        ]
        return (True, None)
    try:
        sb.table("invoices").delete().eq("id", id_value).execute()
    except Exception as e:
        return (False, f"계산서 삭제 실패: {e}")
    st.session_state["invoice_records"] = [
        r for r in st.session_state.get("invoice_records", []) if r.get("id") != id_value
    ]
    return (True, None)

# 기존 탭6 코드 호환용 별칭 (탭6에서 reload_invoice_records(...)를 호출하던 경우)
def reload_invoice_records(year: int | None = None):
    return load_invoices(year)


def get_invoice_year_options() -> list[int]:
    """계산서(invoices) 연도 선택 옵션을 생성합니다.

    - DB(Supabase)가 있으면 invoices.ym 기준으로 최소/최대 연도를 조회해 범위를 생성
    - 세션(invoice_records)에서 파싱 가능한 연도도 포함
    - 항상 올해/작년을 포함(신규/소급 입력 편의)
    """
    years: set[int] = set()

    # 세션에 로드된 계산서에서 연도 수집
    try:
        for r in (st.session_state.get("invoice_records", []) or []):
            ym = r.get("ym")
            if isinstance(ym, str) and len(ym) >= 4:
                try:
                    years.add(int(ym[:4]))
                except Exception:
                    pass
    except Exception:
        pass

    # 항상 올해/작년 포함
    try:
        years.add(int(NOW_KST.year))
        years.add(int(NOW_KST.year) - 1)
    except Exception:
        pass

    # DB가 있으면 invoices 테이블에서 최소/최대 연도 범위 추가
    if sb:
        def _parse_year(v):
            try:
                s = str(v)
                return int(s[:4]) if len(s) >= 4 else None
            except Exception:
                return None
        try:
            rmin = sb.table("invoices").select("ym").order("ym", desc=False).limit(1).execute()
            rmax = sb.table("invoices").select("ym").order("ym", desc=True).limit(1).execute()
            min_y = _parse_year((rmin.data or [{}])[0].get("ym")) if (rmin and hasattr(rmin, "data")) else None
            max_y = _parse_year((rmax.data or [{}])[0].get("ym")) if (rmax and hasattr(rmax, "data")) else None
            if isinstance(min_y, int) and isinstance(max_y, int) and 1900 <= min_y <= max_y <= 3000:
                years.update(range(min_y, max_y + 1))
        except Exception:
            pass

    out = sorted({y for y in years if isinstance(y, int) and 1900 <= y <= 3000})
    return out
# ─────────────────────────────────────────
# (추가 블록 끝)
# ─────────────────────────────────────────

# ============================
# Bootstrapping
# ============================
st.title("팀 수입 관리")
if sb: st.success("✅ Supabase 연결됨 (팀 공동 사용 가능)")
else: st.info("🧪 Supabase 미설정 — 세션 메모리로 동작합니다. 팀 사용은 Secrets에 SUPABASE 설정하세요.")

load_data(); ensure_order("team_members"); ensure_order("locations")

# ← ② 추가 두 줄 (계산서 세션키 보장 + 초기 로드)
st.session_state.setdefault("invoice_records", [])
load_invoices(NOW_KST.year)

st.session_state.setdefault("confirm_target", None)
st.session_state.setdefault("confirm_action", None)
st.session_state.setdefault("edit_income_id", None)
st.session_state.setdefault("confirm_delete_income_id", None)
st.session_state.setdefault("records_page", 0)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["입력", "통계", "정산", "계산서", "기록 관리", "설정"])

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

    # 🔵 추가: 계산서(DB) 최신화 — 나머지 원본은 전부 그대로 유지
    try:
        if "reload_invoice_records" in globals():
            reload_invoice_records(NOW_KST.year)
    except Exception:
        pass

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
    # 하위 탭: 팀원별 / 업체종합 / 업체개별 / 계산서 통계(🔵 추가)
    # ============================
    tab_mem, tab_loc_all, tab_loc_each, tab_invoice = st.tabs(['팀원별', '업체종합', '업체개별', '계산서 통계'])

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
            # 연간 합계 (팀원별) - 총합/보험/비보험
            annual_by_mem_cat = dfY.groupby(['member','category'], dropna=False)['amount'].sum().reset_index()
            annual_pivot = annual_by_mem_cat.pivot(index='member', columns='category', values='amount').fillna(0.0)
            for col in ['보험','비보험']:
                if col not in annual_pivot.columns:
                    annual_pivot[col] = 0.0
            annual_pivot = annual_pivot[['보험','비보험']]
            annual_pivot['총합(만원)'] = annual_pivot['보험'] + annual_pivot['비보험']
            annual_pivot = annual_pivot.sort_values('총합(만원)', ascending=False).reset_index().rename(columns={'member':'팀원'})
            annual_pivot['순위'] = range(1, len(annual_pivot)+1)
            annual_pivot = annual_pivot[['순위','팀원','총합(만원)','보험','비보험']]

            st.markdown('##### 연간 합계 · 총합/보험/비보험')
            st.dataframe(
                annual_pivot,
                use_container_width=True,
                hide_index=True,
                column_config={c: st.column_config.NumberColumn(format='%.0f') for c in ['총합(만원)','보험','비보험']}
            )

            # 월 선택 (보험/비보험 분리) - 다중 선택
            months_avail_all = sorted(dfY['month'].unique().tolist())
            if months_avail_all:
                month_sel2 = st.multiselect(
                    '월 선택(보험/비보험 분리 보기) · 다중 선택 가능',
                    months_avail_all,
                    default=[months_avail_all[-1]],
                    key='mem_month_all_multi'
                )
                month_sel2 = sorted(month_sel2)
                if month_sel2:
                    df_month = dfY[dfY['month'].isin(month_sel2)].copy()
                    by_mem_cat = df_month.groupby(['member','category'], dropna=False)['amount'].sum().reset_index()
                    pivot = by_mem_cat.pivot(index='member', columns='category', values='amount').fillna(0.0)
                    for col in ['보험','비보험']:
                        if col not in pivot.columns: pivot[col] = 0.0
                    pivot = pivot[['보험','비보험']]
                    pivot['총합(만원)'] = pivot['보험'] + pivot['비보험']
                    pivot = pivot.sort_values('총합(만원)', ascending=False).reset_index().rename(columns={'member':'팀원'})

                    months_label = ', '.join([f'{m}월' for m in month_sel2])
                    st.markdown(f'##### {months_label} · 보험/비보험 분리 + 총합')
                    st.dataframe(
                        pivot[['팀원','총합(만원)','보험','비보험']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={c: st.column_config.NumberColumn(format='%.0f') for c in ['총합(만원)','보험','비보험']}
                    )
                else:
                    st.info('월을 1개 이상 선택하세요.')
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

        # 3) 업체 단일 선택  ✅ 커스텀 정렬: [부산숨, 성모안과, 아미유외과, 이진용외과] + 수입입력 탭 원본 순서
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

    # ───────── 4) 계산서 통계 (🔵 추가: DB 연동, 발행금액 내림차순) ─────────
    with tab_invoice:
        st.markdown("#### 계산서 통계")

        # 현재 세션에 있는 데이터(초기값: 올해만 로드될 수 있음)
        inv = st.session_state.get("invoice_records", []) or []

        # 이름 매핑 (표시용)
        mmap = {m.get("id"): m.get("name") for m in (st.session_state.get("team_members",[]) or [])}
        lmap = {l.get("id"): l.get("name") for l in (st.session_state.get("locations",[])   or [])}

        # 드롭다운(팀 전체 + 모든 팀원)
        all_member_names = [m.get("name") for m in (st.session_state.get("team_members",[]) or []) if m.get("name")]
        mem = st.selectbox("팀원 선택", ["팀 전체"] + all_member_names, index=0, key="t2_inv_mem")
        # 연도 선택
        years_avail = get_invoice_year_options()
        y = st.selectbox(
            "연도 선택",
            years_avail,
            index=years_avail.index(NOW_KST.year) if NOW_KST.year in years_avail else len(years_avail)-1,
            key="t2_inv_year"
        )

        # ✅ 선택한 연도의 계산서 데이터를 DB에서 다시 로드 (연도 변경 시에만)
        if sb:
            loaded_y = st.session_state.get("_t2_inv_loaded_year")
            if loaded_y != y:
                load_invoices(y)
                st.session_state["_t2_inv_loaded_year"] = y
        inv = st.session_state.get("invoice_records", []) or []


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
        months_avail = sorted({_ym_month(r.get("ym")) for r in Q if _ym_month(r.get("ym"))})
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





# ============================
# Tab 6: 설정 (팀원/업체 추가·삭제·순서 이동)
# ============================
with tab6:
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
# Tab 5: 기록 관리 (전체 수정/삭제)
# ============================
with tab5:
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
# Tab 3: 정산 (최종본 / 보험·비보험 규칙 포함)
# ============================
with tab3:
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

    # ───────── 고정 이체(항상 포함) ─────────
    FIXED_TRANSFER_FROM = "강현석"
    FIXED_TRANSFER_TO   = "이수성"
    FIXED_TRANSFER_AMT  = 400  # 만원
    FIXED_TRANSFER_MEMO = "고정 이체"

    def _is_fixed_transfer_row(r: dict) -> bool:
        try:
            return (
                _same_person(r.get("from", ""), FIXED_TRANSFER_FROM)
                and _same_person(r.get("to", ""), FIXED_TRANSFER_TO)
                and int(r.get("amount", 0) or 0) == int(FIXED_TRANSFER_AMT)
            )
        except Exception:
            return False

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
        # 기본값: 성모 고정액 1000만원
        sb_upsert_month(ym_key, 1000, bs, am)
        mrow = sb_get_month(ym_key)
    sungmo_fixed = int(mrow["sungmo_fixed"])
    recv_bs = mrow["receiver_busansoom"]   # 부산숨 수령자(허브)
    recv_am = mrow["receiver_amiyou"]      # 아미유 수령자
    recv_lee = "강현석"                    # 성모/이진용 수령자(고정) — 필요 시 DB화 가능

    tab_in, tab_out = st.tabs(["입력", "정산"])

# ==================== 입력 ====================
with tab_in:
    st.markdown("#### 월별 입력")

    # ───────────────── 기본 설정 (항상 펼침) ─────────────────
    with st.container(border=True):
        st.markdown("##### 기본 설정")
        c1, c2, c3 = st.columns(3)
        nf = c1.number_input("성모 고정액(만원)", value=int(sungmo_fixed), step=10, key="inp_fixed")
        nb = c2.selectbox("부산숨 수령자", members_all, index=members_all.index(recv_bs) if recv_bs in members_all else 0, key="inp_recv_bs")
        na = c3.selectbox("아미유 수령자", members_all, index=members_all.index(recv_am) if recv_am in members_all else 0, key="inp_recv_am")

        if st.button("저장", type="primary", key="inp_save_month_conf"):
            sb_upsert_month(ym_key, nf, nb, na)
            st.success("저장되었습니다.")
            st.rerun()

        st.caption("이진용외과 수령자: 강현석 (고정)")

    # ───────────────── 팀비 사용 (항상 펼침) ─────────────────
    with st.container(border=True):
        st.markdown("##### 팀비 사용 입력")
        c1, c2, c3 = st.columns([1, 1, 2])
        w = c1.selectbox("사용자", members_all, key="inp_teamfee_user")
        a = c2.text_input("금액(만원)", "", key="inp_teamfee_amount")
        m = c3.text_input("메모", "", key="inp_teamfee_memo")

        if st.button("팀비 사용 추가", type="primary", key="inp_teamfee_add"):
            if str(a).strip().isdigit():
                sb_add("settlement_teamfee", {"ym_key": ym_key, "who": w, "amount": int(a), "memo": m})
                st.rerun()
            else:
                st.error("금액은 숫자로 입력하세요.")

        st.markdown("###### 팀비 사용 내역")
        tf = sb_list("settlement_teamfee", ym_key)
        if not tf:
            st.caption("아직 팀비 사용 내역이 없습니다.")
        else:
            for r in tf:
                rid = r["id"]
                st.session_state.setdefault(f"tf_edit_{rid}", False)

                row1 = st.columns([1, 1, 2, 1, 1])
                row1[0].write(r["who"])
                row1[1].write(f"{int(r['amount'])}만원")
                row1[2].write(r.get("memo",""))

                # 수정 토글
                if row1[3].button("수정", key=f"tf_btn_edit_{rid}"):
                    st.session_state[f"tf_edit_{rid}"] = not st.session_state[f"tf_edit_{rid}"]

                # 삭제(확인 없이 즉시)
                if row1[4].button("삭제", key=f"tf_btn_del_{rid}"):
                    sb_delete("settlement_teamfee", rid)
                    st.rerun()

                # 편집 영역
                if st.session_state[f"tf_edit_{rid}"]:
                    ec1, ec2, ec3 = st.columns([1, 2, 1])
                    new_a = ec1.text_input("금액", str(int(r["amount"])), key=f"tf_edit_amount_{rid}")
                    new_m = ec2.text_input("메모", r.get("memo",""), key=f"tf_edit_memo_{rid}")
                    if ec3.button("저장", key=f"tf_btn_save_{rid}"):
                        if str(new_a).strip().isdigit():
                            sb_update("settlement_teamfee", rid, {"amount": int(new_a), "memo": new_m})
                            st.session_state[f"tf_edit_{rid}"] = False
                            st.success("수정되었습니다.")
                            st.rerun()
                        else:
                            st.error("금액은 숫자로 입력하세요.")

    # ───────────────── 팀원 간 이체 (항상 펼침 / 수정 가능) ─────────────────
    with st.container(border=True):
        st.markdown("##### 팀원 간 이체 입력")
        # 고정 이체 안내
        if (FIXED_TRANSFER_FROM in members_all) and (FIXED_TRANSFER_TO in members_all):
            st.caption(f"고정 포함: {FIXED_TRANSFER_FROM} → {FIXED_TRANSFER_TO} {FIXED_TRANSFER_AMT}만원")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        f = c1.selectbox("보낸 사람", members_all, key="inp_tr_from")
        t = c2.selectbox("받는 사람", [x for x in members_all if x != f], key="inp_tr_to")
        ta = c3.text_input("금액(만원)", "", key="inp_tr_amount")
        tm = c4.text_input("메모", "", key="inp_tr_memo")

        if st.button("이체 추가", type="primary", key="inp_tr_add"):
            if str(ta).strip().isdigit():
                sb_add("settlement_transfer", {"ym_key": ym_key, "from": f, "to": t, "amount": int(ta), "memo": tm})
                st.rerun()
            else:
                st.error("금액은 숫자로 입력하세요.")

        st.markdown("###### 이체 내역")
        tr = sb_list("settlement_transfer", ym_key)

        # 고정 이체(가상 행) + 사용자 입력 이체(단, 고정과 동일한 행은 중복 방지)
        tr_rows = []
        if (FIXED_TRANSFER_FROM in members_all) and (FIXED_TRANSFER_TO in members_all):
            tr_rows.append({
                "id": "__fixed__",
                "from": FIXED_TRANSFER_FROM,
                "to": FIXED_TRANSFER_TO,
                "amount": FIXED_TRANSFER_AMT,
                "memo": FIXED_TRANSFER_MEMO,
            })
        tr_rows.extend([r for r in tr if not _is_fixed_transfer_row(r)])

        if not tr_rows:
            st.caption("등록된 이체 내역이 없습니다.")
        else:
            for r in tr_rows:
                rid = r["id"]
                if rid != "__fixed__":
                    st.session_state.setdefault(f"tr_edit_{rid}", False)

                row = st.columns([1, 0.3, 1, 2, 1, 1])
                row[0].write(r["from"])
                row[1].write("→")
                row[2].write(r["to"])
                row[3].write(r.get("memo",""))
                row[4].write(f"{int(r['amount'])}만원")

                if rid == "__fixed__":
                    row[5].write("고정")
                else:
                    # 수정 토글
                    if row[4].button("수정", key=f"tr_btn_edit_{rid}"):
                        st.session_state[f"tr_edit_{rid}"] = not st.session_state[f"tr_edit_{rid}"]

                    # 삭제(확인 없이 즉시)
                    if row[5].button("삭제", key=f"tr_btn_del_{rid}"):
                        sb_delete("settlement_transfer", rid)
                        st.rerun()

                # 편집 영역 (보낸사람/받는사람/금액/메모 모두 수정 가능)
                if rid != "__fixed__" and st.session_state[f"tr_edit_{rid}"]:
                    # 현재 값이 members_all에 없을 수도 있으니 방어적으로 index 계산
                    cur_from = r.get("from","")
                    cur_to   = r.get("to","")
                    from_idx = members_all.index(cur_from) if cur_from in members_all else 0
                    to_opts  = [x for x in members_all if x != cur_from]
                    to_idx   = to_opts.index(cur_to) if cur_to in to_opts else 0

                    ec1, ec2, ec3, ec4, ec5 = st.columns([1, 1, 1, 2, 1])
                    new_from = ec1.selectbox("보낸 사람", members_all, index=from_idx, key=f"tr_edit_from_{rid}")
                    # 받는 사람 옵션은 보낸 사람과 달라야 하므로 new_from 기준으로 다시 계산
                    to_opts2 = [x for x in members_all if x != new_from]
                    # 기존 받는 사람이 to_opts2에 없을 수 있으니 방어
                    to_idx2 = to_opts2.index(cur_to) if cur_to in to_opts2 else 0
                    new_to   = ec2.selectbox("받는 사람", to_opts2, index=to_idx2, key=f"tr_edit_to_{rid}")
                    new_amt  = ec3.text_input("금액", str(int(r["amount"])), key=f"tr_edit_amount_{rid}")
                    new_memo = ec4.text_input("메모", r.get("memo",""), key=f"tr_edit_memo_{rid}")

                    if ec5.button("저장", key=f"tr_btn_save_{rid}"):
                        try:
                            amt_int = int(str(new_amt).strip())
                        except:
                            st.error("금액은 숫자로 입력하세요.")
                        else:
                            payload = {"from": new_from, "to": new_to, "amount": amt_int, "memo": new_memo}
                            sb_update("settlement_transfer", rid, payload)
                            st.session_state[f"tr_edit_{rid}"] = False
                            st.success("수정되었습니다.")
                            st.rerun()


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
        # 고정 이체는 항상 포함 (단, 구성원에 없으면 건너뜀)
        if (FIXED_TRANSFER_FROM in members_all) and (FIXED_TRANSFER_TO in members_all) and int(FIXED_TRANSFER_AMT):
            tx.append({
                "from": FIXED_TRANSFER_FROM,
                "to": FIXED_TRANSFER_TO,
                "amount": int(FIXED_TRANSFER_AMT),
                "reason": f"이체:{FIXED_TRANSFER_MEMO}",
            })

        # 사용자 입력 이체 (고정 이체와 동일한 행은 중복 방지)
        for r in tr:
            if _is_fixed_transfer_row(r):
                continue
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
# Tab 4: 계산서 (입력 / 수정·삭제)
# ============================
with tab4:
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        NOW_KST = datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        NOW_KST = datetime.now()

    # ───────────────── Supabase 클라이언트 ─────────────────
    from supabase import create_client

    @st.cache_resource
    def _get_supabase():
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return create_client(url, key)

    _sb = _get_supabase()

    # ───────────────── 컬럼 키 매핑(Camel ↔ snake) ─────────────────
    def _to_db_keys(d: dict) -> dict:
        mapping = {
            "teamMemberId": "team_member_id",
            "locationId": "location_id",
            "insType": "ins_type",
            "issueAmount": "issue_amount",
            "taxAmount": "tax_amount",
            "ym": "ym",
            "id": "id",
        }
        return {mapping.get(k, k): v for k, v in d.items()}

    def _to_client_keys(d: dict) -> dict:
        mapping = {
            "team_member_id": "teamMemberId",
            "location_id": "locationId",
            "ins_type": "insType",
            "issue_amount": "issueAmount",
            "tax_amount": "taxAmount",
            "ym": "ym",
            "id": "id",
        }
        return {mapping.get(k, k): v for k, v in d.items()}

    # ───────────────── 안전 rerun ─────────────────
    def _inv_safe_rerun():
        try:
            st.rerun()
        except AttributeError:
            try:
                st.experimental_rerun()
            except Exception:
                pass

    # ───────────────── 세션 기본값 ─────────────────
    ss = st.session_state
    ss.setdefault("invoice_records", [])
    ss.setdefault("inv_page", 0)
    ss.setdefault("edit_invoice_id", None)
    ss.setdefault("confirm_delete_invoice_id", None)

    # ───────────────── 공통 헬퍼 ─────────────────
    def _name_from(_id: str, coll: list[dict]) -> str:
        for x in coll:
            if x.get("id") == _id:
                return x.get("name", "")
        return ""

    def _member_id_by_name(name: str) -> str | None:
        for m in ss.get("team_members", []):
            if m.get("name") == name:
                return m.get("id")
        return None

    def _loc_id_by_name(name: str) -> str | None:
        for l in ss.get("locations", []):
            if l.get("name") == name:
                return l.get("id")
        return None

    # ───────────────── Supabase CRUD ─────────────────
    def invoice_insert(payload: dict) -> tuple[bool, str | None]:
        """
        payload 예:
        {
          "ym": "2025-11",
          "teamMemberId": "...",
          "locationId": "...",
          "insType": "보험" | "비보험",
          "issueAmount": 120.0,  # 만원
          "taxAmount": 12.0,     # 만원
        }
        """
        try:
            res = _sb.table("invoices").insert(_to_db_keys(payload), returning="representation").execute()
            if getattr(res, "error", None):
                return False, str(res.error)
            return True, None
        except Exception as e:
            return False, str(e)

    def invoice_update(invoice_id: str, patch: dict) -> tuple[bool, str | None]:
        try:
            res = _sb.table("invoices").update(_to_db_keys(patch)).eq("id", invoice_id).execute()
            if getattr(res, "error", None):
                return False, str(res.error)
            return True, None
        except Exception as e:
            return False, str(e)

    def invoice_delete(invoice_id: str) -> bool:
        try:
            res = _sb.table("invoices").delete().eq("id", invoice_id).execute()
            return not bool(getattr(res, "error", None))
        except Exception:
            return False

    def reload_invoice_records(year: int) -> None:
        """지정 연도의 데이터로 ss.invoice_records 갱신 (ym LIKE 'YYYY-%')."""
        try:
            q = (
                _sb.table("invoices")
                  .select("*")
                  .like("ym", f"{year:04d}-%")
                  .order("ym", desc=False)
                  .execute()
            )
            if getattr(q, "error", None):
                st.error(f"계산서 로드 실패: {q.error}")
                return
            rows = q.data or []
            ss.invoice_records = [_to_client_keys(r) for r in rows]
        except Exception as e:
            st.error(f"계산서 로드 실패: {e}")

    # ───────────────── 서브탭 ─────────────────
    tab6_input, tab6_manage = st.tabs(["입력", "수정·삭제"])

    # ============================
    # (1) 입력
    # ============================
    with tab6_input:
        st.subheader("계산서 입력")

        # ⚠️ Streamlit form 내부에서는 위젯 변경 시 스크립트가 재실행되지 않아
        #     (보험/비보험 → 업체 목록) 같은 "의존형" UI가 즉시 갱신되지 않습니다.
        #     → 계산서 입력은 form을 사용하지 않고 버튼 클릭으로 저장합니다.

        # 연/월
        years_avail_all = get_invoice_year_options()
        months_avail_all = list(range(1, 13))

        col_y, col_m = st.columns(2)
        with col_y:
            in_year = st.selectbox("연도", years_avail_all, index=years_avail_all.index(NOW_KST.year), key="inv_in_year")
        with col_m:
            in_month = st.selectbox("월", months_avail_all, index=NOW_KST.month - 1, key="inv_in_month")
        ym = f"{in_year:04d}-{in_month:02d}"

        # 팀원
        member_names = [m.get("name", "") for m in ss.get("team_members", [])]
        member_name = st.selectbox("팀원", member_names, key="inv_member") if member_names else None
        member_id = _member_id_by_name(member_name) if member_name else None

        # 보험/비보험 → 업체
        ins_type = st.radio("구분", ["보험", "비보험"], horizontal=True, index=0, key="inv_ins")
                # Tab1(수입 입력)과 동일한 방식: 선택한 구분에 해당하는 업체만 보여줌
        filtered_locations = [l for l in ss.get("locations", []) if l.get("category") == ins_type]
        loc_options = {l.get("name", ""): l.get("id") for l in filtered_locations if l.get("name")}

        if not loc_options:
            st.warning(f"'{ins_type}' 분류 업체가 없습니다. 설정 탭에서 추가하세요.")

        loc_name = st.selectbox("업체", list(loc_options.keys()) if loc_options else [], key="inv_loc")
        loc_id = loc_options.get(loc_name)

        # 금액
        def _num(v):
            try:
                return float(str(v).replace(",", "").strip())
            except Exception:
                return None

        col_issue, col_tax = st.columns(2)
        with col_issue:
            issue_raw = st.text_input("계산서 발행금액(만원)", "", placeholder="예: 120", key="inv_issue")
        with col_tax:
            tax_raw = st.text_input("세준금(만원)", "", placeholder="예: 12", key="inv_tax")
        issue_amount = _num(issue_raw)
        tax_amount = _num(tax_raw)

        submitted = st.button("계산서 등록", type="primary", use_container_width=True, key="inv_submit")
        if submitted:
            if not (member_id and loc_id and ym and issue_amount is not None and tax_amount is not None and issue_amount >= 0 and tax_amount >= 0):
                st.error("모든 필드를 올바르게 입력하세요.")
            else:
                ok, err = invoice_insert({
                    "ym": ym,
                    "teamMemberId": member_id,
                    "locationId":  loc_id,
                    "insType":     ins_type,
                    "issueAmount": float(issue_amount),
                    "taxAmount":   float(tax_amount),
                })
                if ok:
                    try:
                        reload_invoice_records(in_year)
                    except Exception:
                        pass
                    st.success(f"{ym} 계산서가 저장되었습니다 ✅")
                    _inv_safe_rerun()
                else:
                    st.error(f"저장 실패: {err or '원인 미상'}")

    # ============================
    # (2) 수정·삭제
    # ============================
    with tab6_manage:
        st.subheader("계산서 수정/삭제")

        # 연도 선택 (DB/세션 기반) + 해당 연도 데이터 로드
        years = get_invoice_year_options()
        # 기본 선택: '데이터가 있는 최신 연도' → 없으면 올해
        default_year = NOW_KST.year
        if sb:
            try:
                rmax = sb.table("invoices").select("ym").order("ym", desc=True).limit(1).execute()
                if rmax and getattr(rmax, "data", None):
                    try:
                        default_year = int(str((rmax.data or [{}])[0].get("ym", ""))[:4]) or default_year
                    except Exception:
                        pass
            except Exception:
                pass
        # 세션에 데이터가 있다면 그 최신 연도로 보정
        try:
            sess_years = []
            for _r in (ss.get("invoice_records", []) or []):
                ym = _r.get("ym")
                if isinstance(ym, str) and len(ym) >= 4:
                    try:
                        sess_years.append(int(ym[:4]))
                    except Exception:
                        pass
            if sess_years:
                default_year = max(sess_years)
        except Exception:
            pass

        c1, c2, c3 = st.columns([2, 3, 2])
        with c1:
            year_sel = st.selectbox(
                "연도",
                years,
                index=years.index(default_year) if default_year in years else (years.index(NOW_KST.year) if NOW_KST.year in years else 0),
                key="inv_year_sel"
            )

        # ✅ 선택한 연도의 계산서 데이터를 DB에서 다시 로드 (연도 변경 시에만)
        if sb:
            loaded_y = ss.get("_t6_inv_loaded_year")
            if loaded_y != year_sel:
                load_invoices(year_sel)
                ss["_t6_inv_loaded_year"] = year_sel
                ss["inv_page"] = 0

        inv = ss.get("invoice_records", []) or []
        if not inv:
            st.info(f"{year_sel}년 계산서 데이터가 없습니다. (다른 연도를 선택해 보세요)")
            st.stop()

        # DF 구성
        df = pd.DataFrame([{
            "id": r.get("id"),
            "ym": r.get("ym", ""),
            "year": int(r.get("ym", "0000-00")[:4]) if r.get("ym") else None,
            "month": int(r.get("ym", "0000-00")[5:7]) if r.get("ym") else None,
            "member_id": r.get("teamMemberId"),
            "member": _name_from(r.get("teamMemberId"), ss.get("team_members", [])),
            "location_id": r.get("locationId"),
            "location": _name_from(r.get("locationId"), ss.get("locations", [])),
            "ins_type": r.get("insType", ""),
            "issue": float(r.get("issueAmount", 0) or 0.0),
            "tax":   float(r.get("taxAmount",   0) or 0.0),
        } for r in inv])

        # 연/월/정렬/필터
        with c2:
            months_avail = sorted(df.loc[df["year"] == year_sel, "month"].dropna().unique().tolist())
            month_opts = ["전체"] + months_avail
            month_sel = st.selectbox("월", month_opts, index=0, key="inv_month_sel")
        with c3:
            order_by = st.selectbox("정렬", ["발행금액↓", "발행금액↑", "세준금↓", "세준금↑"], key="inv_order_by")

        c4, c5, c6 = st.columns([2, 2, 2])
        with c4:
            mem_opts = ["전체"] + sorted([m.get("name", "") for m in ss.get("team_members", [])])
            mem_sel = st.selectbox("팀원", mem_opts, index=0, key="inv_mem_sel")
        with c5:
            ins_sel = st.selectbox("구분", ["전체", "보험", "비보험"], index=0, key="inv_ins_sel")
        with c6:
            loc_pool = ss.get("locations", [])
            if ins_sel != "전체":
                loc_pool = [l for l in loc_pool if l.get("category") == ins_sel]
            loc_opts = ["전체"] + [l.get("name", "") for l in loc_pool]
            loc_sel = st.selectbox("업체", loc_opts, index=0, key="inv_loc_sel")

        q = df[df["year"] == year_sel].copy()
        if month_sel != "전체": q = q[q["month"] == month_sel]
        if mem_sel  != "전체": q = q[q["member"] == mem_sel]
        if ins_sel  != "전체": q = q[q["ins_type"] == ins_sel]
        if loc_sel  != "전체": q = q[q["location"] == loc_sel]

        if order_by == "발행금액↓":
            q = q.sort_values(["issue", "id"], ascending=[False, True])
        elif order_by == "발행금액↑":
            q = q.sort_values(["issue", "id"], ascending=[True, True])
        elif order_by == "세준금↓":
            q = q.sort_values(["tax", "id"], ascending=[False, True])
        else:
            q = q.sort_values(["tax", "id"], ascending=[True, True])

        # 페이지네이션
        PAGE_SIZE = 20
        total = len(q); total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
        ss.inv_page = min(ss.inv_page, total_pages - 1)
        ss.inv_page = max(ss.inv_page, 0)

        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("⬅ 이전", disabled=(ss.inv_page == 0), key="inv_prev"):
                ss.inv_page -= 1; _inv_safe_rerun()
        with pc2:
            st.markdown(f"<div style='text-align:center'>페이지 {ss.inv_page+1} / {total_pages} (총 {total}건)</div>", unsafe_allow_html=True)
        with pc3:
            if st.button("다음 ➡", disabled=(ss.inv_page >= total_pages - 1), key="inv_next"):
                ss.inv_page += 1; _inv_safe_rerun()

        start = ss.inv_page * PAGE_SIZE
        page_df = q.iloc[start:start + PAGE_SIZE].copy()

        # 표
        st.markdown("#### 결과 표")
        st.dataframe(
            page_df[["ym", "member", "location", "ins_type", "issue", "tax"]].rename(
                columns={"ym": "연월", "member": "팀원", "location": "업체", "ins_type": "구분", "issue": "발행금액(만원)", "tax": "세준금(만원)"}
            ),
            use_container_width=True,
            column_config={
                "발행금액(만원)": st.column_config.NumberColumn(format="%.0f"),
                "세준금(만원)":   st.column_config.NumberColumn(format="%.0f"),
            }
        )

        # 카드형 수정/삭제
        st.markdown("#### 선택/수정/삭제")
        for _, row in page_df.iterrows():
            with st.container(border=True):
                left, right = st.columns([6, 2])
                left.write(f"**{row['ym']} · {row['member']} · {row['location']} · {row['ins_type']} · 발행 {int(row['issue']):,}만원 / 세준 {int(row['tax']):,}만원**")
                with right:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("🖉 수정", key=f"edit_inv_{row['id']}"):
                            ss.edit_invoice_id = row["id"]; _inv_safe_rerun()
                    with col_b:
                        if st.button("🗑 삭제", key=f"del_inv_{row['id']}"):
                            ss.confirm_delete_invoice_id = row["id"]; _inv_safe_rerun()

        # 삭제 확인
        if ss.confirm_delete_invoice_id:
            rid = ss.confirm_delete_invoice_id
            with st.container(border=True):
                st.error("정말 삭제하시겠습니까? (되돌릴 수 없음)")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ 삭제 확정", key="inv_delete_confirm"):
                        if invoice_delete(rid):
                            ss.confirm_delete_invoice_id = None
                            st.success("삭제되었습니다."); _inv_safe_rerun()
                        else:
                            st.error("삭제 실패(권한/RLS/네트워크)")
                with c2:
                    if st.button("❌ 취소", key="inv_delete_cancel"):
                        ss.confirm_delete_invoice_id = None; _inv_safe_rerun()

        # 수정 폼
        if ss.edit_invoice_id:
            target = next((x for x in ss.invoice_records if x.get("id") == ss.edit_invoice_id), None)
            if target:
                st.markdown("#### 선택한 계산서 수정")

                cur_year  = int(target["ym"][:4]); cur_month = int(target["ym"][5:7])
                cur_member_name = _name_from(target["teamMemberId"], ss.get("team_members", []))
                cur_loc = next((l for l in ss.get("locations", []) if l.get("id") == target.get("locationId")), None)
                cur_ins = target.get("insType", "보험")

                # ⚠️ form 내부에서는 라디오 변경으로 업체 목록이 즉시 갱신되지 않으므로(입력 탭과 동일한 이슈)
                #     수정 UI도 form 대신 버튼 저장 방식으로 구성합니다.
                edit_prefix = f"edit_inv_{target['id']}"

                c1, c2 = st.columns(2)
                with c1:
                    years_all = get_invoice_year_options()
                    if cur_year not in years_all: years_all = sorted(set(years_all + [cur_year]))
                    edit_year  = st.selectbox("연도", years_all, index=years_all.index(cur_year), key=f"{edit_prefix}_year")
                    edit_month = st.selectbox("월", list(range(1, 13)), index=cur_month - 1, key=f"{edit_prefix}_month")

                    member_options = {m.get("name", ""): m.get("id") for m in ss.get("team_members", []) if m.get("name")}
                    member_names = list(member_options.keys()) or [cur_member_name or ""]
                    member_idx = member_names.index(cur_member_name) if (cur_member_name in member_names) else 0
                    member_name_edit = st.selectbox("팀원", member_names, index=member_idx, key=f"{edit_prefix}_member")
                    member_id_edit = member_options.get(member_name_edit) or target.get("teamMemberId")

                with c2:
                    ins_edit = st.radio(
                        "구분",
                        ["보험", "비보험"],
                        index=0 if cur_ins == "보험" else 1,
                        horizontal=True,
                        key=f"{edit_prefix}_ins",
                    )
                    filtered_locs = [l for l in ss.get("locations", []) if l.get("category") == ins_edit and l.get("name")]
                    if filtered_locs:
                        loc_options = {l.get("name", ""): l.get("id") for l in filtered_locs}
                    else:
                        # 현재 선택된 업체라도 표시되게 fallback
                        fallback_name = (_name_from(target.get("locationId"), ss.get("locations", [])) or "")
                        loc_options = {fallback_name: target.get("locationId")}

                    loc_names = list(loc_options.keys())
                    loc_key = f"{edit_prefix}_loc"
                    if loc_names:
                        # 구분 변경 시 선택된 업체가 후보군에 없으면 현재값(가능하면) 또는 첫 항목으로 보정
                        cur_name = cur_loc.get("name") if (cur_loc and cur_loc.get("name")) else None
                        if ss.get(loc_key) not in loc_names:
                            ss[loc_key] = cur_name if (cur_name in loc_names) else loc_names[0]
                    loc_name_edit = st.selectbox("업체", loc_names, key=loc_key)
                    loc_id_edit   = loc_options.get(loc_name_edit)

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    issue_raw_edit = st.text_input(
                        "계산서 발행금액(만원)",
                        value=str(int(float(target.get("issueAmount", 0) or 0))),
                        key=f"{edit_prefix}_issue",
                    )
                with col_e2:
                    tax_raw_edit = st.text_input(
                        "세준금(만원)",
                        value=str(int(float(target.get("taxAmount", 0) or 0))),
                        key=f"{edit_prefix}_tax",
                    )

                def _num_or_none(v):
                    try:
                        return float(str(v).replace(",", "").strip())
                    except Exception:
                        return None

                issue_edit = _num_or_none(issue_raw_edit)
                tax_edit   = _num_or_none(tax_raw_edit)

                b1, b2 = st.columns(2)
                with b1:
                    save_clicked = st.button("✅ 저장", type="primary", use_container_width=True, key=f"{edit_prefix}_save")
                with b2:
                    cancel_clicked = st.button("❌ 취소", use_container_width=True, key=f"{edit_prefix}_cancel")

                if cancel_clicked:
                    ss.edit_invoice_id = None
                    _inv_safe_rerun()

                if save_clicked:
                    if issue_edit is None or tax_edit is None or issue_edit < 0 or tax_edit < 0:
                        st.error("금액은 0 이상의 숫자만 입력하세요.")
                    else:
                        new_payload = {
                            "ym": f"{edit_year:04d}-{edit_month:02d}",
                            "teamMemberId": member_id_edit,
                            "locationId":   loc_id_edit,
                            "insType":      ins_edit,
                            "issueAmount":  float(issue_edit),
                            "taxAmount":    float(tax_edit),
                        }

                        ok, err = invoice_update(target["id"], new_payload)
                        if not ok:
                            st.error(f"저장 실패: {err or '원인 미상'}")
                        else:
                            ss.edit_invoice_id = None
                            try:
                                reload_invoice_records(edit_year)
                            except Exception:
                                pass
                            st.success("수정되었습니다.")
                            _inv_safe_rerun()
