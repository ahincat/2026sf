import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="학생 학습 타이머", page_icon="📚", layout="centered")
DATA_FILE = Path(__file__).with_name("study_records.json")
DEFAULT_SUBJECTS = ["국어", "영어", "수학", "과학", "사회", "기타"]


def load_records():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, ValueError, OSError):
        return []


def save_records(records):
    try:
        DATA_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def format_seconds(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


if "records" not in st.session_state:
    st.session_state.records = load_records()
if "subjects" not in st.session_state:
    st.session_state.subjects = DEFAULT_SUBJECTS.copy()
if "subject" not in st.session_state:
    st.session_state.subject = DEFAULT_SUBJECTS[0]
if "running" not in st.session_state:
    st.session_state.running = False
if "elapsed" not in st.session_state:
    st.session_state.elapsed = 0.0
if "started_at" not in st.session_state:
    st.session_state.started_at = None


def current_elapsed():
    elapsed = st.session_state.elapsed
    if st.session_state.running and st.session_state.started_at is not None:
        elapsed += time.monotonic() - st.session_state.started_at
    return elapsed


def pause():
    if st.session_state.running:
        st.session_state.elapsed = current_elapsed()
        st.session_state.running = False
        st.session_state.started_at = None


def start():
    if not st.session_state.running:
        st.session_state.started_at = time.monotonic()
        st.session_state.running = True


def reset():
    st.session_state.running = False
    st.session_state.elapsed = 0.0
    st.session_state.started_at = None


with st.sidebar:
    st.title("📚 학습 관리")
    page = st.radio("메뉴", ["공부타이머", "오늘 할일", "공부회고"], key="page")
    st.divider()


def show_study_timer():
    st.title("📚 학생 학습 타이머")
    st.caption("과목을 선택하고 공부 시간을 측정해 보세요!")

    with st.sidebar:
        st.header("⚙️ 과목 관리")
        new_subject = st.text_input("새 과목 이름", placeholder="예: 한국사")
        if st.button("과목 추가", use_container_width=True):
            name = new_subject.strip()
            if not name:
                st.warning("과목 이름을 입력하세요.")
            elif name in st.session_state.subjects:
                st.warning("이미 등록된 과목입니다.")
            else:
                st.session_state.subjects.append(name)
                st.success(f"{name} 과목을 추가했습니다.")
        st.info("Streamlit Cloud의 로컬 파일 저장은 재시작/재배포 시 사라질 수 있습니다. CSV로 기록을 내려받아 보관하세요.")

    subject = st.selectbox("공부할 과목", st.session_state.subjects, key="subject", disabled=st.session_state.running or st.session_state.elapsed > 0)

    @st.fragment(run_every="1s")
    def timer_display():
        st.markdown(
            f"<div style='text-align:center;font-size:clamp(3rem,10vw,5rem);font-weight:800;padding:22px 0'>"
            f"{format_seconds(current_elapsed())}</div>",
            unsafe_allow_html=True,
        )
        st.caption("🟢 측정 중" if st.session_state.running else "⏸️ 대기 / 일시정지")


    timer_display()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ 시작", use_container_width=True, disabled=st.session_state.running):
            start()
            st.rerun()
    with col2:
        if st.button("⏸️ 일시정지", use_container_width=True, disabled=not st.session_state.running):
            pause()
            st.rerun()
    with col3:
        if st.button("🔄 초기화", use_container_width=True):
            reset()
            st.rerun()

    if st.button("💾 현재 공부 시간 기록하기", type="primary", use_container_width=True):
        pause()
        seconds = int(current_elapsed())
        if seconds < 1:
            st.warning("1초 이상 공부한 후 기록해 주세요.")
        else:
            st.session_state.records.append({
                "날짜": datetime.now().strftime("%Y-%m-%d"),
                "시각": datetime.now().strftime("%H:%M:%S"),
                "과목": st.session_state.subject,
                "공부시간(초)": seconds,
            })
            saved = save_records(st.session_state.records)
            reset()
            st.success("공부 시간이 기록되었습니다!" + ("" if saved else " (파일 저장 실패: CSV로 내려받으세요.)"))
            st.rerun()

    st.divider()
    st.subheader("📊 과목별 공부 기록")
    records = st.session_state.records
    if records:
        df = pd.DataFrame(records)
        totals = df.groupby("과목", as_index=False)["공부시간(초)"].sum()
        totals["총 공부 시간"] = totals["공부시간(초)"].map(format_seconds)
        a, b = st.columns(2)
        a.metric("총 공부 시간", format_seconds(df["공부시간(초)"].sum()))
        b.metric("총 학습 횟수", f"{len(df)}회")
        st.dataframe(totals[["과목", "총 공부 시간"]], hide_index=True, use_container_width=True)
        st.bar_chart(totals.set_index("과목")["공부시간(초)"], x_label="과목", y_label="공부 시간(초)")
        st.subheader("🗓️ 상세 기록")
        detail = df.copy()
        detail["공부 시간"] = detail["공부시간(초)"].map(format_seconds)
        st.dataframe(detail[["날짜", "시각", "과목", "공부 시간"]].iloc[::-1], hide_index=True, use_container_width=True)
        st.download_button("⬇️ 기록 CSV 다운로드", data=df.to_csv(index=False).encode("utf-8-sig"), file_name="study_records.csv", mime="text/csv", use_container_width=True)
        if st.button("🗑️ 모든 기록 삭제"):
            st.session_state.records = []
            save_records([])
            st.rerun()
    else:
        st.info("아직 기록이 없습니다. 공부를 시작하고 시간을 기록해 보세요!")


if page == "공부타이머":
    show_study_timer()
elif page == "오늘 할일":
    st.title("📝 오늘 할일")
else:
    st.title("✍️ 공부회고")
