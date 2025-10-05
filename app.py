# ============================
# app.py (AgGrid 버전: 설정탭 내 셀버튼)
# ============================
import streamlit as st
import pandas as pd
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- 임시 데이터 (GitHub 업로드용 예시) ---
if "team_members" not in st.session_state:
    st.session_state.team_members = [
        {"id": "m_1", "name": "홍길동", "order": 0},
        {"id": "m_2", "name": "김철수", "order": 1},
    ]
if "locations" not in st.session_state:
    st.session_state.locations = [
        {"id": "l_1", "name": "서울센터", "category": "보험", "order": 0},
        {"id": "l_2", "name": "부산지점", "category": "비보험", "order": 1},
    ]

def swap_order(target_key, i, j):
    data = st.session_state[target_key]
    data[i]["order"], data[j]["order"] = data[j]["order"], data[i]["order"]
    st.session_state[target_key] = sorted(data, key=lambda x: x["order"])

def delete_row(target_key, rid):
    st.session_state[target_key] = [x for x in st.session_state[target_key] if x["id"] != rid]

def upsert_row(target_key, row):
    found = False
    for x in st.session_state[target_key]:
        if x["id"] == row["id"]:
            x.update(row)
            found = True
    if not found:
        st.session_state[target_key].append(row)

def ensure_order(target_key):
    for idx, item in enumerate(sorted(st.session_state[target_key], key=lambda x: x["order"])):
        item["order"] = idx

# --- 페이지 설정 ---
st.set_page_config(page_title="Team Income App (AgGrid)", layout="wide")

tab1, tab2, tab3 = st.tabs(["수입입력", "통계", "설정"])

# --- Tab 3: 설정 ---
with tab3:
    st.subheader("설정")
    st.caption("📱 모바일에서는 표를 가로로 스크롤하여 ▲ / ▼ / 🗑 버튼을 눌러 조작하세요.")

    ACTIONS_CELL_RENDERER = JsCode("""
    class BtnCellRenderer {
      init(params){
        const wrap = document.createElement('div');
        wrap.style.display = 'flex';
        wrap.style.gap = '6px';
        wrap.style.alignItems = 'center';
        wrap.innerHTML = `
          <button data-action="up" title="위로" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:8px;cursor:pointer;">▲</button>
          <button data-action="down" title="아래로" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:8px;cursor:pointer;">▼</button>
          <button data-action="delete" title="삭제" style="padding:4px 8px;border:1px solid #ef4444;border-radius:8px;color:#ef4444;cursor:pointer;">🗑</button>
        `;
        this.eGui = wrap;
        this.clickHandler = (e) => {
          const act = e.target && e.target.dataset ? e.target.dataset.action : null;
          if (act){ params.node.setDataValue('pending_action', act); }
        };
        wrap.addEventListener('click', this.clickHandler);
      }
      getGui(){ return this.eGui; }
      refresh(){ return false; }
      destroy(){ if(this.eGui){ this.eGui.removeEventListener('click', this.clickHandler);} }
    }
    """)

    def _df_members():
        tm = sorted(st.session_state.team_members, key=lambda x: x.get("order", 0))
        df = pd.DataFrame(tm)
        if df.empty: return df
        df = df[["name","order","id"]].rename(columns={"name":"이름","order":"순서","id":"ID"})
        df.insert(0,"동작","")
        df["pending_action"] = ""
        return df

    def _aggrid_table(df):
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_column("동작", header_name="동작", cellRenderer=ACTIONS_CELL_RENDERER, editable=False, width=120)
        gb.configure_column("이름", editable=True)
        gb.configure_column("순서", editable=True)
        gb.configure_column("ID", hide=True)
        gb.configure_column("pending_action", hide=True)
        go = gb.build()
        resp = AgGrid(df, gridOptions=go, height=300, allow_unsafe_jscode=True,
                      update_mode=GridUpdateMode.MODEL_CHANGED, fit_columns_on_grid_load=True)
        return resp

    st.markdown("### 👤 팀원 관리")
    with st.form("add_member_form", clear_on_submit=True):
        new_member = st.text_input("새 팀원 이름","")
        if st.form_submit_button("팀원 추가"):
            if new_member.strip():
                mid = f"m_{datetime.utcnow().timestamp()}"
                next_order = (max([x.get("order",0) for x in st.session_state.team_members] or [-1]) + 1)
                upsert_row("team_members", {"id":mid,"name":new_member.strip(),"order":next_order})
                st.success("팀원 추가 완료"); st.rerun()
            else:
                st.error("이름을 입력하세요.")

    df_tm = _df_members()
    if not df_tm.empty:
        res = _aggrid_table(df_tm)
        df_after = res["data"]
        if isinstance(df_after, pd.DataFrame):
            for _, row in df_after.iterrows():
                for tm in st.session_state.team_members:
                    if tm["id"] == row["ID"]:
                        tm["name"] = row["이름"]
                        tm["order"] = int(row["순서"])
            tm_sorted = sorted(st.session_state.team_members, key=lambda x: x.get("order",0))
            id_to_idx = {tm["id"]:i for i,tm in enumerate(tm_sorted)}
            for _, row in df_after.iterrows():
                act = str(row.get("pending_action","")).lower()
                rid = row["ID"]
                if not act: continue
                i = id_to_idx.get(rid,None)
                if i is None: continue
                if act == "up" and i>0:
                    swap_order("team_members", i, i-1)
                elif act == "down" and i < len(tm_sorted)-1:
                    swap_order("team_members", i, i+1)
                elif act == "delete":
                    delete_row("team_members", rid)
            ensure_order("team_members")

    st.divider()

    st.markdown("### 🏢 업체 관리")
    cat_view = st.radio("보기(카테고리)",["보험","비보험"],horizontal=True)
    locs = [l for l in st.session_state.locations if l["category"]==cat_view]
    locs = sorted(locs,key=lambda x:x.get("order",0))
    df_lc = pd.DataFrame(locs)
    if not df_lc.empty:
        df_lc = df_lc[["name","order","id","category"]].rename(columns={"name":"업체명","order":"순서","id":"ID","category":"분류"})
        df_lc.insert(0,"동작","")
        df_lc["pending_action"] = ""
        gb = GridOptionsBuilder.from_dataframe(df_lc)
        gb.configure_column("동작", header_name="동작", cellRenderer=ACTIONS_CELL_RENDERER, editable=False, width=120)
        gb.configure_column("업체명", editable=True)
        gb.configure_column("순서", editable=True)
        gb.configure_column("분류", editable=False)
        gb.configure_column("ID", hide=True)
        gb.configure_column("pending_action", hide=True)
        go = gb.build()
        res2 = AgGrid(df_lc, gridOptions=go, height=300, allow_unsafe_jscode=True,
                      update_mode=GridUpdateMode.MODEL_CHANGED, fit_columns_on_grid_load=True)
        df_after2 = res2["data"]
        if isinstance(df_after2, pd.DataFrame):
            for _, row in df_after2.iterrows():
                for lc in st.session_state.locations:
                    if lc["id"] == row["ID"]:
                        lc["name"] = row["업체명"]
                        lc["order"] = int(row["순서"])
            loc_sorted = sorted(st.session_state.locations, key=lambda x:x.get("order",0))
            id_to_idx2 = {lc["id"]:i for i,lc in enumerate(loc_sorted)}
            for _, row in df_after2.iterrows():
                act = str(row.get("pending_action","")).lower()
                rid = row["ID"]
                if not act: continue
                i = id_to_idx2.get(rid,None)
                if i is None: continue
                if act == "up" and i>0:
                    swap_order("locations", i, i-1)
                elif act == "down" and i < len(loc_sorted)-1:
                    swap_order("locations", i, i+1)
                elif act == "delete":
                    delete_row("locations", rid)
            ensure_order("locations")

    st.divider()
    if st.button("데이터 새로고침"):
        ensure_order("team_members")
        ensure_order("locations")
        st.success("새로고침 완료")
        st.rerun()
