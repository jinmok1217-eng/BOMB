import json
import os
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# ✅ 페이지 설정 (모바일 친화적)
st.set_page_config(
    page_title="야구부 라인업 빌더",
    page_icon="⚾",
    layout="centered",  # ← 모바일 최적화
    initial_sidebar_state="collapsed"
)

DATA_FILE = "baseball_members.json"

POSITIONS = ["투수", "포수", "1루수", "2루수", "3루수", "유격수", "좌익수", "중견수", "우익수"]
POS_CODE = {
    "투수": "P", "포수": "C", "1루수": "1B", "2루수": "2B", "3루수": "3B",
    "유격수": "SS", "좌익수": "LF", "중견수": "CF", "우익수": "RF"
}
CODE_TO_POS = {v: k for k, v in POS_CODE.items()}

INITIAL_MEMBERS = [
    {"name": "유진목", "pos1": "2루수", "pos2": "유격수"},
    {"name": "안다훈", "pos1": "1루수", "pos2": "투수"},
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

def compute_lineup(attendees):
    if not attendees:
        return {}, [], []

    assigned = {}
    used_names = set()

    def get_score(member, pos):
        if member["pos1"] == pos:
            return 100
        if member["pos2"] == pos:
            return 40
        return 5

    pos_demand = []
    for pos in POSITIONS:
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

        if chosen["pos1"] == pos:
            r_type = "1지망 우선 배정"
        elif chosen["pos2"] == pos:
            r_type = "2지망 배정"
        else:
            r_type = "조정 배정"

        reasons.append({
            "pos": pos,
            "assigned": chosen,
            "p1_list": item["p1"],
            "p2_list": item["p2"],
            "reason": r_type
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

# ✅ 타이틀
st.title("⚾ 야구부 라인업 빌더")
st.caption("희망 포지션 기반 자동 배정 및 실시간 편집")

tab_lineup, tab_members, tab_stats, tab_backup = st.tabs([
    "📋 경기 라인업", 
    "👥 선수 명단 관리", 
    "📊 포지션 지원 현황", 
    "💾 백업/파일"
])

# ─────────────────────────────────------------------
# TAB 1: 경기 라인업
# ─────────────────────────────────------------------
with tab_lineup:
    st.subheader("오늘 경기 참석자 선택")

    member_names = [m["name"] for m in st.session_state.members]

    col_att_ctrl1, col_att_ctrl2 = st.columns([1, 4])
    with col_att_ctrl1:
        select_all = st.checkbox("전체 선수 참석", value=True)

    default_selected = member_names if select_all else []
    selected_attendees = st.multiselect(
        "참석자 선택",
        options=member_names,
        default=default_selected
    )

    if st.button("⚡ 최적 라인업 자동 생성", use_container_width=True):
        attendee_objs = [m for m in st.session_state.members if m["name"] in selected_attendees]
        if len(attendee_objs) < 9:
            st.warning(f"선택된 참석자가 {len(attendee_objs)}명입니다. 정규 수비진을 구성하려면 9명 이상이 필요합니다.")
            st.session_state.lineup, st.session_state.bench, st.session_state.reasons = compute_lineup(attendee_objs)
        else:
            lineup, bench, reasons = compute_lineup(attendee_objs)
            st.session_state.lineup = lineup
            st.session_state.bench = bench
            st.session_state.reasons = reasons
            st.success("라인업 생성 완료!")

    if st.session_state.lineup:

        with st.expander("🔄 수동 위치 맞교환 (스왑)", expanded=False):
            c_swap1, c_swap2, c_swap_btn = st.columns([2, 2, 1])
            with c_swap1:
                pos_a = st.selectbox("포지션 1", POSITIONS, key="swap_a")
            with c_swap2:
                pos_b = st.selectbox("포지션 2", [p for p in POSITIONS if p != pos_a], key="swap_b")
            with c_swap_btn:
                st.write("")
                if st.button("변경", use_container_width=True):
                    if pos_a in st.session_state.lineup and pos_b in st.session_state.lineup:
                        temp = st.session_state.lineup[pos_a]
                        st.session_state.lineup[pos_a] = st.session_state.lineup[pos_b]
                        st.session_state.lineup[pos_b] = temp
                        st.toast(f"{pos_a}와 {pos_b}의 담당 선수가 맞교환되었습니다.")
                        st.rerun()

        col_field, col_summary = st.columns([3, 2])

        # 야구장 다이아몬드 시각화
        with col_field:
            st.write("⚾ 야구장 수비 위치 배치도")

            field_coords = {
                "투수": (50, 62), "포수": (50, 88), "1루수": (76, 56),
                "2루수": (63, 41), "3루수": (24, 56), "유격수": (37, 41),
                "좌익수": (18, 20), "중견수": (50, 12), "우익수": (82, 20)
            }

            pins_html = ""
            for pos, (x, y) in field_coords.items():
                player = st.session_state.lineup.get(pos)
                if player:
                    p_name = player["name"]
                    p1 = player["pos1"]
                    p2 = player["pos2"]
                    if p1 == pos:
                        badge = "<span style='color:#34d399;font-size:9px;'>[1지망]</span>"
                        bg = "#064e3b"
                        border = "#10b981"
                    elif p2 == pos:
                        badge = "<span style='color:#38bdf8;font-size:9px;'>[2지망]</span>"
                        bg = "#0c4a6e"
                        border = "#0ea5e9"
                    else:
                        badge = "<span style='color:#fbbf24;font-size:9px;'>[조정]</span>"
                        bg = "#451a03"
                        border = "#f59e0b"
                    wish = f"<div style='font-size:9px;color:#94a3b8;'>희망:{p1}/{p2}</div>"
                else:
                    p_name = "공석"
                    badge = ""
                    bg = "#1e293b"
                    border = "#475569"
                    wish = ""

                pins_html += f"""
                <div style="position:absolute;left:{x}%;top:{y}%;transform:translate(-50%,-50%);z-index:10;">
                    <div style="background:{bg};border:1.5px solid {border};border-radius:10px;padding:4px 8px;text-align:center;color:white;box-shadow:0 4px 6px -1px rgba(0,0,0,0.5);min-width:68px;">
                        <div style="font-size:10px;font-weight:bold;color:#fcd34d;">{pos} {badge}</div>
                        <div style="font-size:12px;font-weight:800;margin-top:2px;">{p_name}</div>
                        {wish}
                    </div>
                </div>
                """

            field_html = f"""
            <div style="position:relative;width:100%;aspect-ratio:4/3;background:#022c22;border-radius:16px;border:2px solid #065f46;overflow:hidden;box-shadow:inset 0 2px 8px rgba(0,0,0,0.8);">
                <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0.25;pointer-events:none;">
                    <div style="width:45%;aspect-ratio:1/1;border:2px solid #fef08a;transform:rotate(45deg);margin-top:55px;"></div>
                </div>
                {pins_html}
            </div>
            """
            components.html(field_html, height=360)

        # 우측 배정표
        with col_summary:
            st.write("📋 선발 9인 명단")

            lineup_rows = []
            for pos in POSITIONS:
                player = st.session_state.lineup.get(pos)
                if player:
                    lineup_rows.append({
                        "포지션": pos,
                        "선수 이름": player["name"],
                        "1지망": player["pos1"],
                        "2지망": player["pos2"]
                    })
                else:
                    lineup_rows.append({
                        "포지션": pos, "선수 이름": "공석", "1지망": "-", "2지망": "-"
                    })

            st.dataframe(pd.DataFrame(lineup_rows), use_container_width=True, hide_index=True)

            # 벤치 후보
            st.write(f"🪑 대기 후보 (벤치 {len(st.session_state.bench)}명)")
            if st.session_state.bench:
                bench_str = ", ".join([f"{m['name']}({m['pos1']}/{m['pos2']})" for m in st.session_state.bench])
                st.info(bench_str)
            else:
                st.write("참석자 전원이 선발로 배정되었습니다.")

        st.divider()

        # ✅ 포지션별 배정 현황 (간결화)
        st.subheader("📍 포지션별 배정 및 지원 현황")

        for pos in POSITIONS:
            with st.expander(f"📌 {pos}"):
                assigned_player = st.session_state.lineup.get(pos)
                assigned_name = assigned_player["name"] if assigned_player else "공석"

                st.write(f"**배정된 선수**: {assigned_name}")

                r_item = next((r for r in st.session_state.reasons if r["pos"] == pos), None)
                p1_names = r_item["p1_list"] if r_item else []
                p2_names = r_item["p2_list"] if r_item else []

                st.write(f"1순위 지망 ({len(p1_names)}명): {', '.join(p1_names) if p1_names else '-'}")
                st.write(f"2순위 지망 ({len(p2_names)}명): {', '.join(p2_names) if p2_names else '-'}")

# ─────────────────────────────────------------------
# TAB 2: 선수 명단 관리
# ─────────────────────────────────------------------
with tab_members:
    st.subheader("선수 명단 즉시 수정")
    st.caption("표 안의 셀을 클릭하여 수정 가능. 저장 버튼 클릭 시 반영됩니다.")

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
        if st.button("💾 변경사항 저장", use_container_width=True):
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
            st.success(f"{len(updated_list)}명 정보 저장 완료!")
            st.rerun()

    with col_reset:
        if st.button("초기 명단 복구", use_container_width=True):
            st.session_state.members = INITIAL_MEMBERS
            save_members(INITIAL_MEMBERS)
            st.warning("초기 24명 명단으로 복구되었습니다.")
            st.rerun()

# ─────────────────────────────────------------------
# TAB 3: 포지션별 지원 현황
# ─────────────────────────────────------------------
with tab_stats:
    st.subheader("포지션별 지원자 분포")

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
                st.write(", ".join(p1_list) if p1_list else "-")

                st.write(f":blue[2순위 ({len(p2_list)}명)]")
                st.write(", ".join(p2_list) if p2_list else "-")

# ─────────────────────────────────------------------
# TAB 4: 백업 및 파일 관리
# ─────────────────────────────────------------------
with tab_backup:
    st.subheader("데이터 백업 및 CSV 내보내기")
    st.write("명단을 CSV로 저장하거나 업로드하여 복원할 수 있습니다.")

    df_export = pd.DataFrame(st.session_state.members)
    df_export.rename(columns={"name": "이름", "pos1": "1순위포지션", "pos2": "2순위포지션"}, inplace=True)
    csv_data = df_export.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label="📥 CSV 다운로드",
        data=csv_data,
        file_name="야구부_회원명단.csv",
        mime="text/csv",
        type="primary"
    )

    st.divider()
    st.subheader("백업 파일 업로드")
    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            imported_members = []
            for _, row in df_uploaded.iterrows():
                imported_members.append({
                    "name": str(row.get("이름", "")).strip(),
                    "pos1": str(row.get("1순위포지션", "")).strip(),
                    "pos2": str(row.get("2순위포지션", "")).strip()
                })
            if st.button("업로드한 명단 적용", use_container_width=True):
                st.session_state.members = imported_members
                save_members(imported_members)
                st.success(f"{len(imported_members)}명의 명단을 불러왔습니다.")
                st.rerun()
        except Exception as e:
            st.error(f"파일 처리 중 오류 발생: {e}")
