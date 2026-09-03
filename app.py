import json
import os
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(
    page_title="야구부 라인업 빌더",
    page_icon="⚾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

DATA_FILE = "baseball_members.json"

POSITIONS = ["포수", "1루수", "2루수", "3루수", "유격수", "좌익수", "중견수", "우익수", "투수"]
POS_CODE = {
    "포수": "C", "1루수": "1B", "2루수": "2B", "3루수": "3B",
    "유격수": "SS", "좌익수": "LF", "중견수": "CF", "우익수": "RF",
    "투수": "P"
}
CODE_TO_POS = {v: k for k, v in POS_CODE.items()}

INITIAL_MEMBERS = [
    {"name": "유진목", "pos1": "2루수", "pos2": "유격수"},
    {"name": "안다훈", "pos1": "1루수", "pos2": "포수"},
    {"name": "김민준", "pos1": "1루수", "pos2": "3루수"},
    {"name": "김민준(22)", "pos1": "3루수", "pos2": "유격수"},
    {"name": "전겸", "pos1": "유격수", "pos2": "유격수"},
    {"name": "고현웅", "pos1": "유격수", "pos2": "좌익수"},
    {"name": "장호진(22)", "pos1": "우익수", "pos2": "2루수"},
    {"name": "정지오(22)", "pos1": "2루수", "pos2": "우익수"},
    {"name": "추희창(23)", "pos1": "중견수", "pos2": "우익수"},
    {"name": "강재원", "pos1": "2루수", "pos2": "3루수"},
    {"name": "조수민(25)", "pos1": "3루수", "pos2": "좌익수"},
    {"name": "이창민(23)", "pos1": "유격수", "pos2": "중견수"},
    {"name": "김경원", "pos1": "1루수", "pos2": "중견수"},
    {"name": "이승재", "pos1": "1루수", "pos2": "2루수"},
    {"name": "김도현", "pos1": "우익수", "pos2": "1루수"},
    {"name": "이창훈", "pos1": "3루수", "pos2": "유격수"},
    {"name": "최민준(26)", "pos1": "중견수", "pos2": "1루수"},
    {"name": "이유준(25)", "pos1": "포수", "pos2": "2루수"},
    {"name": "나규영(24)", "pos1": "유격수", "pos2": "3루수"},
    {"name": "이창민(26)", "pos1": "2루수", "pos2": "좌익수"},
    {"name": "채정현(26)", "pos1": "중견수", "pos2": "좌익수"},
    {"name": "안유준(24)", "pos1": "2루수", "pos2": "좌익수"},
    {"name": "김도안(25)", "pos1": "포수", "pos2": "3루수"},
    {"name": "임서준", "pos1": "3루수", "pos2": "좌익수"}
]

def load_members():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return INITIAL_MEMBERS
    return INITIAL_MEMBERS

def save_members(members):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(members, f, ensure_ascii=False, indent=2)

if "members" not in st.session_state:
    st.session_state.members = load_members()

if "lineup" not in st.session_state:
    st.session_state.lineup = {}

if "bench" not in st.session_state:
    st.session_state.bench = []

if "reasons" not in st.session_state:
    st.session_state.reasons = []

# 수동 라인업 생성
def build_manual_lineup(selections):
    lineup = {}
    selected_names = set()
    for pos, name in selections.items():
        if name and name != "" and name != "---":
            lineup[pos] = {"name": name, "pos1": "", "pos2": ""}
            selected_names.add(name)
    # 수동 선택 선수의 pos1/pos2 정보 붙이기
    for pos, player in lineup.items():
        for m in st.session_state.members:
            if m["name"] == player["name"]:
                player["pos1"] = m["pos1"]
                player["pos2"] = m["pos2"]
                break
    return lineup, selected_names

# 자동 라인업 산출 알고리즘 (투수 제외 8개 수비 포지션)
def compute_lineup(attendees):
    if not attendees:
        return {}, [], []

    assigned = {}
    used_names = set()
    auto_positions = [p for p in POSITIONS if p != "투수"]

    def get_score(member, pos):
        if member["pos1"] == pos:
            return 100
        if member["pos2"] == pos:
            return 40
        return 5

    pos_demand = []
    for pos in auto_positions:
        p1 = [m["name"] for m in attendees if m["pos1"] == pos]
        p2 = [m["name"] for m in attendees if m["pos2"] == pos]
        pos_demand.append({
            "pos": pos,
            "p1": p1,
            "p2": p2,
            "total_demand": len(p1) + len(p2)
        })
    pos_demand.sort(key=lambda x: x["total_demand"])

    reasons = []
    for item in pos_demand:
        pos = item["pos"]
        candidates = [m for m in attendees if m["name"] not in used_names]
        if not candidates:
            break

        candidates.sort(key=lambda m: get_score(m, pos), reverse=True)
        chosen = candidates[0]
        assigned[pos] = chosen
        used_names.add(chosen["name"])

        reasons.append({
            "pos": pos,
            "assigned": chosen,
            "p1_list": item["p1"],
            "p2_list": item["p2"],
        })

    improved = True
    iterations = 0
    while improved and iterations < 30:
        improved = False
        iterations += 1
        pos_keys = list(assigned.keys())
        for i in range(len(pos_keys)):
            for j in range(i + 1, len(pos_keys)):
                p1 = pos_keys[i]
                p2 = pos_keys[j]
                m1 = assigned[p1]
                m2 = assigned[p2]

                cur_score = get_score(m1, p1) + get_score(m2, p2)
                swp_score = get_score(m1, p2) + get_score(m2, p1)

                if swp_score > cur_score:
                    assigned[p1] = m2
                    assigned[p2] = m1
                    improved = True

    bench = [m for m in attendees if m["name"] not in used_names]
    return assigned, bench, reasons


# UI 시작
st.title("⚾ 야구부 라인업 빌더")
st.caption("희망 포지션 기반 자동 배정, 상세 사유 분석 및 즉시 명단 편집기")

tab_lineup, tab_members, tab_stats, tab_backup = st.tabs([
    "📋 경기 라인업", 
    "👥 선수 명단 관리/수정", 
    "📊 포지션별 지망 현황", 
    "💾 백업 및 파일 관리"
])

# ─── 참석자 선택 스타일 (남색 테마) ───
st.markdown("""
<style>
.stMultiSelect [data-baseweb="multiselect"] .css-191i9si {
    border-color: #1e3a5f !important;
    background-color: #eef2ff !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-191i9si:hover {
    border-color: #3b82f6 !important;
    background-color: #e0e7ff !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-191i9si:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-1p8n2gn {
    background-color: #1e3a5f !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-1p8n2gn:hover {
    background-color: #3b82f6 !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-1u27aoq {
    background-color: #0f172a !important;
    border-radius: 0 6px 6px 0 !important;
}
.stMultiSelect [data-baseweb="multiselect"] .css-1u27aoq:hover {
    background-color: #1e3a5f !important;
}
.stSelectbox [data-baseweb="select"] .css-191i9si {
    border-color: #1e3a5f !important;
}
.stSelectbox [data-baseweb="select"] .css-191i9si:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
}
/* 수동 라인업 빌더 드롭다운 스타일 */
.stSelectbox [data-baseweb="select"] .css-1u27aoq {
    background-color: #1e3a5f !important;
    border-radius: 0 6px 6px 0 !important;
}
.stSelectbox [data-baseweb="select"] .css-1u27aoq:hover {
    background-color: #3b82f6 !important;
}
</style>
""", unsafe_allow_html=True)

with tab_lineup:
    st.subheader("오늘 경기 참석자 선택")
    member_names = [m["name"] for m in st.session_state.members]
    
    selected_attendees = st.multiselect(
        "참석자 선택",
        options=member_names,
        default=member_names
    )

    # ─── 라인업 생성 방식 선택 ───
    st.divider()
    st.subheader("라인업 생성 방식")
    gen_method = st.radio(
        "생성 방법 선택",
        ["⚡ 자동 라인업 생성 (알고리즘)", "✏️ 수동으로 직접 라인업 구성"],
        horizontal=True,
        key="gen_method"
    )

    if gen_method == "⚡ 자동 라인업 생성 (알고리즘)":
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button("⚡ 최적 라인업 자동 생성", type="primary", use_container_width=True):
                attendee_objs = [m for m in st.session_state.members if m["name"] in selected_attendees]
                if len(attendee_objs) < 8:
                    st.warning(f"선택된 참석자가 {len(attendee_objs)}명입니다. 최소 8명 이상 필요합니다.")
                    st.stop()
                
                lineup, bench, reasons = compute_lineup(attendee_objs)
                st.session_state.lineup = lineup
                st.session_state.bench = bench
                st.session_state.reasons = reasons
                st.success("라인업 생성이 완료되었습니다!")
                st.rerun()

    else:  # 수동 라인업
        st.caption("각 포지션별로 1지망, 2지망, 미지망 중에서 직접 선택해 라인업을 구성하세요.")
        st.divider()

        att_objs = [m for m in st.session_state.members if m["name"] in selected_attendees]
        
        with st.expander("🔧 수동 라인업 구성 패널", expanded=True):
            st.write("참석자 목록에서 각 포지션의 선수를 선택하세요. 공석을 원하면 '--- 공석 ---'을 선택하세요.")
            
            # 포지션별 선택 드롭다운 (1지망/2지망/미지망 옵션)
            manual_selections = {}
            manual_cols = st.columns(3)
            for idx, pos in enumerate(POSITIONS):
                col = manual_cols[idx % 3]
                with col:
                    # 옵션 구성: 미지망 + 1지망 선수 + 2지망 선수 + 공석
                    p1_names = [m["name"] for m in att_objs if m["pos1"] == pos]
                    p2_names = [m["name"] for m in att_objs if m["pos2"] == pos]
                    
                    options = ["--- 공석 ---"]
                    seen = set()
                    for n in p1_names + p2_names:
                        if n not in seen:
                            options.append(n)
                            seen.add(n)
                    options.sort()
                    
                    current_val = st.session_state.lineup.get(pos, {}).get("name", "") if st.session_state.lineup else ""
                    if current_val == "":
                        current_val = "--- 공석 ---"
                    
                    key = f"manual_{pos}"
                    manual_selections[pos] = st.selectbox(
                        f"{pos} ({POS_CODE[pos]})",
                        options=options,
                        index=options.index(current_val) if current_val in options else 0,
                        key=key
                    )
            
            col_man_save, col_man_clear = st.columns([1, 1])
            with col_man_save:
                if st.button("✅ 수동 라인업 적용", type="primary", use_container_width=True):
                    lineup, selected_names = build_manual_lineup(manual_selections)
                    st.session_state.lineup = lineup
                    
                    # 벤치 계산: 참석자 중 선발에 안 뽑힌 사람
                    all_selected = set(m["name"] for m in att_objs)
                    bench = [m for m in att_objs if m["name"] not in selected_names]
                    st.session_state.bench = bench
                    
                    # reasons 초기화 (수동이라 사유 없음)
                    st.session_state.reasons = []
                    for pos in POSITIONS:
                        assigned = lineup.get(pos)
                        if assigned:
                            p1_list = [m["name"] for m in att_objs if m["pos1"] == pos]
                            p2_list = [m["name"] for m in att_objs if m["pos2"] == pos]
                            st.session_state.reasons.append({
                                "pos": pos,
                                "assigned": assigned,
                                "p1_list": p1_list,
                                "p2_list": p2_list,
                            })
                        else:
                            p1_list = [m["name"] for m in att_objs if m["pos1"] == pos]
                            p2_list = [m["name"] for m in att_objs if m["pos2"] == pos]
                            st.session_state.reasons.append({
                                "pos": pos,
                                "assigned": None,
                                "p1_list": p1_list,
                                "p2_list": p2_list,
                            })
                    
                    st.success("수동 라인업이 적용되었습니다!")
                    st.rerun()
            
            with col_man_clear:
                if st.button("🔄 수동 선택 초기화", use_container_width=True):
                    for pos in POSITIONS:
                        st.session_state[lineup_key] = st.session_state.get(f"manual_{pos}")
                    st.warning("수동 선택 값이 초기화되었습니다. 다시 선택해주세요.")
                    st.rerun()

    # ─── 라인업 표시 (공통) ───
    if st.session_state.lineup:

        with st.expander("🔄 수동 위치 맞교환 (스왑)"):
            c_swap1, c_swap2, c_swap_btn = st.columns([2, 2, 1])
            with c_swap1:
                pos_a = st.selectbox("맞바꿀 포지션 1", POSITIONS, key="swap_a")
            with c_swap2:
                pos_b = st.selectbox("맞바꿀 포지션 2", [p for p in POSITIONS if p != pos_a], key="swap_b")
            with c_swap_btn:
                st.write("")
                st.write("")
                if st.button("위치 변경", use_container_width=True):
                    if pos_a in st.session_state.lineup and pos_b in st.session_state.lineup:
                        temp = st.session_state.lineup[pos_a]
                        st.session_state.lineup[pos_a] = st.session_state.lineup[pos_b]
                        st.session_state.lineup[pos_b] = temp
                        st.toast(f"{pos_a}와 {pos_b}의 담당 선수가 맞교환되었습니다.")
                        st.rerun()

        col_field, col_summary = st.columns([3, 2])

        # ─── 야구장 그라운드 (잔디 초록 + 마운드) ───
        with col_field:
            st.write("⚾ 야구장 수비 위치 배치도")

            field_coords = {
                "포수": (50, 88), "1루수": (76, 56),
                "2루수": (63, 41), "3루수": (24, 56),
                "유격수": (37, 41),
                "좌익수": (18, 20), "중견수": (50, 12), "우익수": (82, 20),
                "투수": (50, 52)
            }

            pins_html = ""
            for pos, (x, y) in field_coords.items():
                player = st.session_state.lineup.get(pos)
                if player:
                    p_name = player["name"]
                    p1 = player.get("pos1", "")
                    p2 = player.get("pos2", "")
                    if pos == "투수":
                        bg = "#1e293b"
                        border = "#64748b"
                        label_color = "#94a3b8"
                    elif p1 == pos:
                        bg = "#1e3a5f"
                        border = "#3b82f6"
                        label_color = "#93c5fd"
                    elif p2 == pos:
                        bg = "#172554"
                        border = "#6366f1"
                        label_color = "#a5b4fc"
                    else:
                        bg = "#0f172a"
                        border = "#818cf8"
                        label_color = "#c4b5fd"
                else:
                    p_name = "공석"
                    bg = "#1e293b"
                    border = "#475569"
                    label_color = "#94a3b8"

                pins_html += f"""
                <div style="position:absolute;left:{x}%;top:{y}%;transform:translate(-50%,-50%);z-index:10;" class="pin_box" data-pos="{pos}">
                    <div style="background:{bg};border:1.5px solid {border};border-radius:8px;padding:2px 6px;text-align:center;color:white;font-size:9px;box-shadow:0 2px 4px -1px rgba(0,0,0,0.4);min-width:50px;line-height:1.3;cursor:pointer;">
                        <div style="font-weight:bold;color:{label_color};font-size:8px;">{pos}</div>
                        <div style="font-weight:800;font-size:10px;margin-top:1px;">{p_name}</div>
                    </div>
                </div>
                """

            field_html = f"""
            <div style="position:relative;width:100%;aspect-ratio:4/3;background:#0f6b3a;border-radius:16px;border:2px solid #0a4d2a;overflow:hidden;box-shadow:inset 0 2px 10px rgba(0,0,0,0.35);">
                <div style="position:absolute;inset:0;opacity:0.25;pointer-events:none;
                    background:radial-gradient(ellipse at 50% 50%, #128040 0%, #0f6b3a 60%, #0a4d2a 100%);">
                </div>
                <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;">
                    <div style="width:45%;aspect-ratio:1/1;background:#a9714d;transform:rotate(45deg);margin-top:55px;
                        border:1px solid #8b5a2b;border-radius:4px;opacity:0.85;">
                    </div>
                </div>
                <div style="position:absolute;left:50%;top:52%;transform:translate(-50%,-50%);
                    width:8%;aspect-ratio:1/1;background:#a9714d;border-radius:50%;
                    border:1px solid #8b5a2b;box-shadow:0 2px 6px rgba(0,0,0,0.3);pointer-events:none;">
                </div>
                {pins_html}
                <script>
                document.querySelectorAll('.pin_box').forEach(box => {{
                    box.addEventListener('click', function() {{
                        const pos = this.getAttribute('data-pos');
                        window.parent.postMessage({{ type: 'position_click', pos: pos }}, '*');
                    }});
                }});
                </script>
            </div>
            """
            components.html(field_html, height=360)

        with col_summary:
            st.write("📋 선발 명단")
            lineup_rows = []
            for pos in POSITIONS:
                player = st.session_state.lineup.get(pos)
                if player:
                    lineup_rows.append({
                        "포지션": pos,
                        "선수 이름": player["name"],
                    })
                else:
                    lineup_rows.append({
                        "포지션": pos, "선수 이름": "공석"
                    })
            st.dataframe(pd.DataFrame(lineup_rows), use_container_width=True, hide_index=True)

            st.write(f"🪑 대기 후보 (벤치 {len(st.session_state.bench)}명)")
            if st.session_state.bench:
                bench_items = []
                for m in st.session_state.bench:
                    p1 = m["pos1"]
                    bench_items.append(f"• {m['name']}  (1지망: {p1})")
                bench_str = "\n".join(bench_items)
                st.info(bench_str)
            else:
                st.write("참석자 전원이 선발로 배정되었습니다.")

        st.divider()
        st.subheader("포지션별 지원자")
        st.caption("포지션별로 누가 지원했는지(1지망/2지망)와 실제 배정 결과만 표시합니다.")

        reason_cols = st.columns(3)
        for idx, pos in enumerate(POSITIONS):
            col = reason_cols[idx % 3]
            with col:
                assigned_player = st.session_state.lineup.get(pos)
                assigned_name = assigned_player["name"] if assigned_player else "공석"
                
                r_item = next((r for r in st.session_state.reasons if r["pos"] == pos), None)
                if r_item:
                    p1_names = ", ".join(r_item["p1_list"]) if r_item["p1_list"] else "없음"
                    p2_names = ", ".join(r_item["p2_list"]) if r_item["p2_list"] else "없음"
                else:
                    p1_list = [m["name"] for m in st.session_state.members if m["pos1"] == pos]
                    p2_list = [m["name"] for m in st.session_state.members if m["pos2"] == pos]
                    p1_names = ", ".join(p1_list) if p1_list else "없음"
                    p2_names = ", ".join(p2_list) if p2_list else "없음"

                with st.container(border=True):
                    st.markdown(f"**{pos}** → **{assigned_name}**")
                    st.caption(f"1지망: {p1_names}")
                    st.caption(f"2지망: {p2_names}")

with tab_members:
    st.subheader("선수 명단 즉시 수정 (Data Editor)")
    st.caption("표 안의 이름이나 포지션 셀을 더블 클릭하면 즉시 수정할 수 있습니다. 아래 [명단 변경사항 저장] 버튼을 누르면 영구 보관됩니다.")

    df_current = pd.DataFrame(st.session_state.members)
    df_current.rename(columns={"name": "이름", "pos1": "1순위포지션", "pos2": "2순위포지션"}, inplace=True)

    edited_df = st.data_editor(
        df_current,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "이름": st.column_config.TextColumn("선수 이름", required=True),
            "1순위포지션": st.column_config.SelectboxColumn("1순위 희망", options=POSITIONS, required=True),
            "2순위포지션": st.column_config.SelectboxColumn("2순위 희망", options=POSITIONS, required=True)
        },
        key="member_editor"
    )

    col_save, col_reset = st.columns([2, 1])
    with col_save:
        if st.button("💾 명단 변경사항 파일에 저장하기", type="primary", use_container_width=True):
            updated_list = []
            for _, row in edited_df.iterrows():
                if pd.notna(row["이름"]) and str(row["이름"]).strip():
                    updated_list.append({
                        "name": str(row["이름"]).strip(),
                        "pos1": str(row["1순위포지션"]).strip(),
                        "pos2": str(row["2순위포지션"]).strip()
                    })
            st.session_state.members = updated_list
            save_members(updated_list)
            st.success(f"총 {len(updated_list)}명의 선수 정보가 안전하게 저장되었습니다!")
            st.rerun()

    with col_reset:
        if st.button("초기 명단(24명)으로 되돌리기", use_container_width=True):
            st.session_state.members = INITIAL_MEMBERS
            save_members(INITIAL_MEMBERS)
            st.warning("스크린샷 기반 초기 24명 명단으로 복구되었습니다.")
            st.rerun()

with tab_stats:
    st.subheader("포지션별 지원자 분포 현황")
    st.caption("포지션별 1순위 및 2순위 지망 인명 분포입니다.")

    stat_cols = st.columns(3)
    for idx, pos in enumerate(POSITIONS):
        col = stat_cols[idx % 3]
        p1_list = [m["name"] for m in st.session_state.members if m["pos1"] == pos]
        p2_list = [m["name"] for m in st.session_state.members if m["pos2"] == pos]
        
        with col:
            with st.container(border=True):
                st.markdown(f"**{pos}** ({POS_CODE[pos]})")
                st.caption(f"총 지원: {len(p1_list) + len(p2_list)}명")
                
                st.write(f":green[1순위 ({len(p1_list)}명)]")
                if p1_list:
                    st.write(", ".join(p1_list))
                else:
                    st.write("-")

                st.write(f":blue[2순위 ({len(p2_list)}명)]")
                if p2_list:
                    st.write(", ".join(p2_list))
                else:
                    st.write("-")

with tab_backup:
    st.subheader("데이터 백업 및 엑셀 내보내기")
    st.write("등록된 선수 명단을 CSV 파일로 다운로드하거나 기존 백업 파일을 업로드하여 복원할 수 있습니다.")

    df_export = pd.DataFrame(st.session_state.members)
    df_export.rename(columns={"name": "이름", "pos1": "1순위포지션", "pos2": "2순위포지션"}, inplace=True)
    csv_data = df_export.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label="📥 엑셀용 CSV 파일 다운로드",
        data=csv_data,
        file_name="야구부_회원명단.csv",
        mime="text/csv",
        type="primary"
    )

    st.divider()
    st.subheader("백업 파일 업로드")
    uploaded_file = st.file_uploader("CSV 파일 업로드 (이름, 1순위포지션, 2순위포지션 열 포함)", type=["csv"])
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            imported_members = []
            for _, row in df_uploaded.iterrows():
                imported_members.append({
                    "name": str(row["이름"]).strip(),
                    "pos1": str(row["1순위포지션"]).strip(),
                    "pos2": str(row["2순위포지션"]).strip()
                })
            if st.button("업로드한 명단 적용하기"):
                st.session_state.members = imported_members
                save_members(imported_members)
                st.success(f"{len(imported_members)}명의 명단을 새로 불러왔습니다.")
                st.rerun()
        except Exception as e:
            st.error(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
