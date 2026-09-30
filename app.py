import re
import time
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import study_guard

st.set_page_config(
    page_title="FlowState - Multi-Modal StudyGuard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Cyber-Minimalist Theme
st.markdown("""
<style>
.stApp { background:#080b11; color:#f0f4f8; font-family:'Segoe UI', system-ui, sans-serif; }
.security-banner {
    padding:10px 16px; margin-bottom:12px; border-radius:10px;
    background:linear-gradient(90deg, #0d1520 0%, #111a26 100%);
    border:1px solid #00d9a6; display:flex; justify-content:space-between;
    align-items:center; font-size:13px; font-weight:700; color:#00e5a3;
}
.telemetry-card {
    background:#0f1722; border:1px solid #1e293b; border-radius:12px;
    padding:12px 14px; margin-bottom:8px;
}
.telemetry-label {
    font-size:11px; text-transform:uppercase; letter-spacing:1px;
    color:#8fa0b5; margin-bottom:4px; font-weight:700;
}
.state-pill {
    display:inline-block; padding:4px 10px; border-radius:14px;
    font-size:12px; font-weight:700; letter-spacing:0.5px;
}
.state-focused { background:rgba(0, 220, 130, 0.15); color:#00e695; border:1px solid #00c878; }
.state-passive { background:rgba(255, 170, 0, 0.15); color:#ffb703; border:1px solid #ffaa00; }
.state-distracted { background:rgba(255, 60, 60, 0.15); color:#ff4d4d; border:1px solid #ff3333; }
.privacy-tag {
    padding:6px 12px; border-radius:8px; border:1px solid #00c878;
    text-align:center; color:#00e695; background:rgba(0,200,120,.06);
    font-size:11px; font-weight:600; margin-top:10px;
}
.parent-nudge-card {
    background:linear-gradient(90deg, rgba(2, 132, 199, 0.25) 0%, rgba(0, 229, 163, 0.25) 100%);
    border:1px solid #38bdf8; border-radius:10px; padding:10px 16px; color:#e0f2fe;
    font-size:14px; font-weight:700; margin-bottom:12px; display:flex; align-items:center; gap:8px;
}
.parent-mobile-card {
    background:#0f1722; border:1px solid #1e293b; border-radius:16px;
    padding:18px; margin-bottom:14px; box-shadow:0 4px 20px rgba(0,0,0,0.4);
}
.whatsapp-btn {
    display:inline-block; background:#25D366; color:#ffffff !important;
    font-weight:700; font-size:13px; padding:8px 16px; border-radius:8px;
    text-decoration:none; margin-top:8px;
}
div[data-testid="stMetric"] {
    background:#0f1722; border:1px solid #1e293b;
    border-radius:12px; padding:10px;
}
</style>
""", unsafe_allow_html=True)

FRAME_SKIP = 3
DISTRACTION_THRESHOLD = 0.35
LEFT_EYE, RIGHT_EYE, NOSE = 33, 263, 1
MODEL_PATH = Path(__file__).parent / "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)

# Detect if accessed via Parent Mobile mode
query_view = st.query_params.get("view", "")
is_parent_mode = (query_view == "parent")

# Generate Local Network URL & QR Code for Parent Phone
local_ip = study_guard.get_local_ip()
parent_mobile_url = f"http://{local_ip}:8501?view=parent"
parent_qr_b64 = study_guard.get_qr_code_base64(parent_mobile_url)

# Initialize Session State
defaults = {
    "camera": None,
    "face_mesh": None,
    "active": False,
    "last_ts": 0,
    "started_at": None,
    "last_tick": None,
    "target_minutes": 45,
    "parent_phone": "+91 ",
    "focused_time": 0.0,
    "reading_time": 0.0,
    "passive_media_time": 0.0,
    "distracted_time": 0.0,
    "distraction_count": 0,
    "passive_media_count": 0,
    "status": "Focused",
    "status_state": "FOCUSED_ACTIVE",
    "status_reason": "Session initialized",
    "frame_count": 0,
    "ratio": 0.0,
    "shield_mode": "minimize",
    "custom_study_topics_str": "math, physics, chemistry, biology, calculus, coding, python, lecture, tutorial, course, cs50, khan academy, one shot, revision, exam, dsa, engineering, notes, explained, gate, jee, neet, upsc",
    "custom_blocklist_str": "shorts, music, song, trailer, gameplay, meme, vlog, funny, comedy, prank, mrbeast, gaming, netflix, twitch, prime video, steam, discord, vlc, reddit, twitter, tiktok",
    "guard": None,
    "latest_telemetry": {},
    "final_summary": None,
    "auto_alert_distraction": True,
    "auto_alert_completion": True,
    "direct_msg_text": "",
    "last_direct_dispatch_status": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def parse_keywords(text: str):
    return [w.strip().lower() for w in text.split(",") if w.strip()]

custom_study_topics = parse_keywords(st.session_state.custom_study_topics_str)
custom_block_keywords = parse_keywords(st.session_state.custom_blocklist_str)

if st.session_state.guard is None:
    st.session_state.guard = study_guard.MultiModalStudyGuard(
        shield_mode=st.session_state.shield_mode,
        custom_study_topics=custom_study_topics,
        custom_block_keywords=custom_block_keywords
    )
else:
    st.session_state.guard.update_settings(
        shield_mode=st.session_state.shield_mode,
        custom_study_topics=custom_study_topics,
        custom_block_keywords=custom_block_keywords
    )

def elapsed_time() -> float:
    if st.session_state.started_at is None:
        return 0.0
    return time.monotonic() - st.session_state.started_at

def target_duration_seconds() -> float:
    return float(st.session_state.target_minutes * 60)

def remaining_time() -> float:
    target = target_duration_seconds()
    elapsed = elapsed_time()
    return max(0.0, target - elapsed)

def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def focus_score() -> float:
    elapsed = elapsed_time()
    if elapsed <= 0:
        return 100.0
    return float(np.clip((st.session_state.focused_time / elapsed) * 100.0, 0.0, 100.0))

def spatial_ratio(landmarks, width: int) -> Optional[float]:
    try:
        left = landmarks[LEFT_EYE]
        right = landmarks[RIGHT_EYE]
        nose = landmarks[NOSE]
        left_x, right_x, nose_x = left.x * width, right.x * width, nose.x * width
        midpoint = (left_x + right_x) / 2
        eye_distance = abs(right_x - left_x)
        if eye_distance < 1e-6:
            return None
        return abs(nose_x - midpoint) / eye_distance
    except (IndexError, AttributeError, TypeError):
        return None

def release_resources() -> None:
    if st.session_state.camera is not None:
        try:
            st.session_state.camera.release()
        except Exception:
            pass
    if st.session_state.face_mesh is not None:
        try:
            st.session_state.face_mesh.close()
        except Exception:
            pass
    st.session_state.camera = None
    st.session_state.face_mesh = None

def start_session() -> bool:
    release_resources()
    if not MODEL_PATH.exists():
        st.error(
            f"Model file not found: {MODEL_PATH.name}. Download it once from {MODEL_URL} "
            "and place it next to app.py."
        )
        return False
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        camera.release()
        return False

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    options = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    mesh = vision.FaceLandmarker.create_from_options(options)

    st.session_state.camera = camera
    st.session_state.face_mesh = mesh
    st.session_state.last_ts = 0
    st.session_state.active = True
    st.session_state.started_at = time.monotonic()
    st.session_state.last_tick = None
    st.session_state.focused_time = 0.0
    st.session_state.reading_time = 0.0
    st.session_state.passive_media_time = 0.0
    st.session_state.distracted_time = 0.0
    st.session_state.distraction_count = 0
    st.session_state.passive_media_count = 0
    st.session_state.status = "Focused"
    st.session_state.status_state = "FOCUSED_ACTIVE"
    st.session_state.status_reason = "Active Study Session"
    st.session_state.frame_count = 0
    st.session_state.ratio = 0.0
    st.session_state.latest_telemetry = {}
    st.session_state.final_summary = None

    # Reset shield statistics
    st.session_state.guard.shield.total_blocked_count = 0
    st.session_state.guard.shield.blocked_history.clear()

    # Sync to shared parent state
    study_guard.update_shared_state({
        "active": True,
        "target_minutes": st.session_state.target_minutes,
        "parent_phone": st.session_state.parent_phone,
        "started_at": time.strftime("%H:%M:%S"),
        "elapsed_seconds": 0.0,
        "remaining_seconds": target_duration_seconds(),
        "focused_time": 0.0,
        "reading_time": 0.0,
        "passive_media_time": 0.0,
        "distracted_time": 0.0,
        "focus_score": 100.0,
        "distraction_count": 0,
        "passive_media_count": 0,
        "total_blocked_apps": 0,
        "status": "Attentive Study Active",
        "status_state": "FOCUSED_ACTIVE",
        "status_reason": "Session started",
        "blocked_history": [],
    })
    return True

def stop_session() -> None:
    if not st.session_state.active:
        return
    st.session_state.final_summary = {
        "target_mins": st.session_state.target_minutes,
        "elapsed": elapsed_time(),
        "focused": st.session_state.focused_time,
        "reading": st.session_state.reading_time,
        "passive_media": st.session_state.passive_media_time,
        "distracted": st.session_state.distracted_time,
        "score": focus_score(),
        "distractions": st.session_state.distraction_count,
        "passive_incidents": st.session_state.passive_media_count,
        "total_blocked_apps": st.session_state.guard.shield.total_blocked_count,
        "blocked_history": list(st.session_state.guard.shield.blocked_history),
        "parent_phone": st.session_state.parent_phone,
    }
    st.session_state.active = False
    release_resources()

    # Sync session stop to parent state
    study_guard.update_shared_state({
        "active": False,
        "status": "Session Ended",
        "status_state": "SESSION_ENDED",
        "status_reason": "Student completed or paused session",
    })

    # Automatically dispatch report directly to parent mobile if enabled
    if st.session_state.get("auto_alert_completion", True):
        p_num = st.session_state.parent_phone.strip()
        clean_p = re.sub(r'[^0-9]', '', p_num)
        if len(clean_p) >= 7:
            report_msg = (
                f"🏆 FlowState Verified Study Report:\n"
                f"• Target Goal: {st.session_state.final_summary['target_mins']} mins\n"
                f"• Study Time: {format_time(st.session_state.final_summary['elapsed'])}\n"
                f"• Focus Score: {st.session_state.final_summary['score']:.1f}%\n"
                f"• Deep Focus: {format_time(st.session_state.final_summary['focused'])}\n"
                f"• Distractions Blocked: {st.session_state.final_summary['total_blocked_apps']} apps\n"
                f"Verified by FlowState StudyGuard AI."
            )
            res = study_guard.send_direct_message(p_num, report_msg, provider="auto")
            st.session_state.last_direct_dispatch_status = res

def process_frame(frame: np.ndarray) -> np.ndarray:
    frame = cv2.flip(frame, 1)
    st.session_state.frame_count += 1
    h, w = frame.shape[:2]

    landmarks = None
    ratio = None

    if st.session_state.frame_count % FRAME_SKIP == 0 and st.session_state.face_mesh is not None:
        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts = max(int(time.monotonic() * 1000), st.session_state.last_ts + 1)
        st.session_state.last_ts = ts
        results = st.session_state.face_mesh.detect_for_video(mp_image, ts)

        if results.face_landmarks:
            landmarks = results.face_landmarks[0]
            ratio = spatial_ratio(landmarks, w)
            if ratio is not None:
                st.session_state.ratio = ratio

        # Multi-modal behavioral & visual fusion evaluation + Smart YouTube & App Shield enforcement
        eval_res = st.session_state.guard.evaluate(
            landmarks=landmarks,
            frame=frame,
            head_ratio=ratio,
            distraction_threshold=DISTRACTION_THRESHOLD,
        )
        st.session_state.latest_telemetry = eval_res

        new_state = eval_res["state"]
        prev_state = st.session_state.status_state

        if new_state == "PASSIVE_MEDIA" and prev_state != "PASSIVE_MEDIA":
            st.session_state.passive_media_count += 1
        elif new_state == "DISTRACTED_AWAY" and prev_state != "DISTRACTED_AWAY":
            st.session_state.distraction_count += 1

        st.session_state.status_state = new_state
        st.session_state.status = eval_res["label"]
        st.session_state.status_reason = eval_res["reason"]

    # Continuous timing tracking
    now = time.monotonic()
    if st.session_state.last_tick is not None:
        delta = min(max(now - st.session_state.last_tick, 0.0), 1.0)
        curr_state = st.session_state.status_state
        if curr_state in ("FOCUSED_ACTIVE", "FOCUSED_READING"):
            st.session_state.focused_time += delta
            if curr_state == "FOCUSED_READING":
                st.session_state.reading_time += delta
        elif curr_state == "PASSIVE_MEDIA":
            st.session_state.passive_media_time += delta
        elif curr_state == "DISTRACTED_AWAY":
            st.session_state.distracted_time += delta
    st.session_state.last_tick = now

    # Sync live state for Parent Mobile view
    tele = st.session_state.latest_telemetry
    study_guard.update_shared_state({
        "active": True,
        "elapsed_seconds": elapsed_time(),
        "remaining_seconds": remaining_time(),
        "focused_time": st.session_state.focused_time,
        "reading_time": st.session_state.reading_time,
        "passive_media_time": st.session_state.passive_media_time,
        "distracted_time": st.session_state.distracted_time,
        "focus_score": focus_score(),
        "distraction_count": st.session_state.distraction_count,
        "passive_media_count": st.session_state.passive_media_count,
        "total_blocked_apps": st.session_state.guard.shield.total_blocked_count,
        "status": st.session_state.status,
        "status_state": st.session_state.status_state,
        "status_reason": st.session_state.status_reason,
        "active_window": tele.get("win_title", "Unknown"),
        "active_app": tele.get("proc_name", "unknown"),
        "app_category": tele.get("app_cat", "NEUTRAL"),
        "is_study_video": tele.get("is_study_video", False),
        "blocked_history": list(st.session_state.guard.shield.blocked_history),
        "parent_phone": st.session_state.parent_phone,
    })

    # Render Clean High-Tech HUD Video Overlay
    color = tele.get("color", (0, 220, 0))
    label = tele.get("label", "FOCUSED")
    app_cat = tele.get("app_cat", "NEUTRAL")
    idle_s = tele.get("idle_sec", 0.0)
    is_study_vid = tele.get("is_study_video", False)
    rem_s = remaining_time()

    # Frame border HUD
    cv2.rectangle(frame, (10, 10), (w - 10, h - 10), color, 4)

    # Top Status Banner Box
    cv2.rectangle(frame, (18, 18), (w - 18, 64), (12, 18, 26), -1)
    cv2.rectangle(frame, (18, 18), (w - 18, 64), color, 1)
    cv2.putText(frame, f"STATUS: {label}", (30, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.68, color, 2, cv2.LINE_AA)

    # In-video live countdown clock (Top right)
    rem_txt = f"LEFT: {format_time(rem_s)}"
    cv2.putText(frame, rem_txt, (w - 210, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 240, 255), 2, cv2.LINE_AA)

    # Bottom Multi-Modal Telemetry HUD
    cv2.rectangle(frame, (18, h - 40), (w - 18, h - 14), (10, 15, 22), -1)
    type_tag = "[ONLINE LECTURE]" if is_study_vid else ("[STUDYING]" if "FOCUSED" in st.session_state.status_state else "[DISTRACTION]")
    sub_hud = f"Input: {int(idle_s)}s  |  App: {app_cat}  |  {type_tag}"
    cv2.putText(frame, sub_hud, (28, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 230, 240), 1, cv2.LINE_AA)

    # Check for Parent Encouragement Nudge on video HUD
    latest_nudge = study_guard.get_latest_parent_nudge()
    if latest_nudge:
        nudge_text = f"Parent: {latest_nudge['message']}"
        cv2.rectangle(frame, (18, 70), (w - 18, 104), (2, 84, 130), -1)
        cv2.putText(frame, nudge_text[:50], (28, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2, cv2.LINE_AA)

    # Automated direct alert trigger if prolonged inattentive viewing/distraction occurs (>30s)
    if st.session_state.get("auto_alert_distraction", True):
        cur_distracted = st.session_state.distracted_time
        if cur_distracted >= 30.0:
            study_guard.check_and_trigger_distraction_alert(
                st.session_state.parent_phone,
                cur_distracted,
                active_window=tele.get("win_title", ""),
                cooldown_seconds=300.0
            )

    return frame

# ==============================================================================
# ========================= PARENT MOBILE PORTAL VIEW ==========================
# ==============================================================================
if is_parent_mode:
    st.markdown("""
    <div style="background:linear-gradient(90deg, #0284c7 0%, #00e5a3 100%); padding:16px 20px; border-radius:14px; margin-bottom:16px; color:#031321;">
        <div style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:1px;">👨‍👩‍👦 FlowState Parent Portal</div>
        <div style="font-size:24px; font-weight:900; margin-top:2px;">Live Mobile Study Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    @st.fragment(run_every=1.0)
    def parent_live_monitor():
        state = study_guard.get_shared_state()
        is_active = state.get("active", False)

        p_phone = state.get("parent_phone", "")
        if p_phone.strip():
            st.caption(f"📱 Connected Parent Phone: **{p_phone.strip()}**")

        if not is_active:
            st.markdown("""
            <div class="parent-mobile-card" style="text-align:center; padding:30px 20px;">
                <div style="font-size:42px; margin-bottom:10px;">⏸️</div>
                <div style="font-size:20px; font-weight:800; color:#f8fafc;">No Active Study Session</div>
                <div style="font-size:13px; color:#94a3b8; margin-top:6px;">
                    This mobile dashboard will automatically begin live tracking as soon as your student clicks <b>Start Session</b>.
                </div>
            </div>
            """, unsafe_allow_html=True)
            return

        # Active Session Metrics
        elapsed = state.get("elapsed_seconds", 0.0)
        remaining = state.get("remaining_seconds", 0.0)
        target_m = state.get("target_minutes", 45)
        score = state.get("focus_score", 100.0)
        status_lbl = state.get("status", "Studying")
        status_state = state.get("status_state", "FOCUSED_ACTIVE")
        reason = state.get("status_reason", "")
        active_win = state.get("active_window", "")
        blocked_cnt = state.get("total_blocked_apps", 0)
        deep_focus = state.get("focused_time", 0.0)
        is_study_vid = state.get("is_study_video", False)

        prog = min(1.0, elapsed / max(1.0, target_m * 60))
        prog_pct = int(prog * 100)
        status_color = "#00e5a3" if "FOCUSED" in status_state else ("#ffb703" if "PASSIVE" in status_state else "#ff4d4d")

        # 1. Main Status Card
        st.markdown(f"""
        <div class="parent-mobile-card" style="border-left:5px solid {status_color};">
            <div style="font-size:11px; font-weight:700; color:#8fa0b5; text-transform:uppercase;">Current Attention Status</div>
            <div style="font-size:26px; font-weight:900; color:{status_color}; margin-top:4px;">
                {status_lbl}
            </div>
            <div style="font-size:14px; color:#cbd5e1; margin-top:6px;">
                <b>Activity:</b> {active_win if active_win else 'Active study window'}
            </div>
            <div style="font-size:12px; color:#94a3b8; margin-top:2px;">
                {reason}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Sprint Progress & Live Countdown
        st.markdown(f"""
        <div class="parent-mobile-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:11px; font-weight:700; color:#8fa0b5; text-transform:uppercase;">Time Remaining</div>
                    <div style="font-size:32px; font-weight:900; color:#00e5a3; font-family:'Segoe UI', monospace; letter-spacing:1px;">
                        {format_time(remaining)}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px; color:#94a3b8;">Goal: <b>{target_m} mins</b></div>
                    <div style="font-size:20px; font-weight:800; color:#38bdf8;">{prog_pct}% Done</div>
                </div>
            </div>
            <div style="background:#17202e; border-radius:10px; height:12px; width:100%; overflow:hidden; border:1px solid #253346; margin-top:12px;">
                <div style="background:linear-gradient(90deg, #0284c7 0%, #00e5a3 100%); height:100%; width:{prog_pct}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. Quick Metrics 2x2 Grid
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Focus Score", f"{score:.1f}%")
            st.metric("Deep Study Time", format_time(deep_focus))
        with c2:
            st.metric("Distractions Intercepted", f"{blocked_cnt} apps")
            st.metric("Study Mode", "Online Lecture" if is_study_vid else "Active Working")

        # 4. Shield Interception Feed
        hist = state.get("blocked_history", [])
        if hist:
            st.markdown("### 🛡️ Distractions Blocked On Student PC")
            for item in hist[:4]:
                st.markdown(f"""
                <div style="background:rgba(255,60,60,0.1); border:1px solid #ff4d4d; border-radius:8px; padding:8px 12px; margin-bottom:6px; font-size:13px;">
                    🚫 <b>{item.get('app','')}</b> ({item.get('action','')})<br>
                    <span style="font-size:11px; color:#94a3b8;">{item.get('title','')} • {item.get('timestamp','')}</span>
                </div>
                """, unsafe_allow_html=True)
        # Direct Messages Sent to Parent Mobile
        direct_msgs = state.get("direct_messages", [])
        if direct_msgs:
            st.markdown("### 📩 Messages Sent Directly to This Phone")
            for d in direct_msgs[:4]:
                msg_body = d.get('message','').replace('\n', '<br>')
                st.markdown(f"""
                <div style="background:#0f1c2e; border-left:4px solid #38bdf8; border-radius:8px; padding:10px 14px; margin-bottom:8px; font-size:13px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#38bdf8;">To: {d.get('phone')}</span>
                        <span style="font-size:11px; color:#94a3b8;">{d.get('timestamp')}</span>
                    </div>
                    <div style="color:#e2e8f0; margin-top:5px; font-size:13px; line-height:1.4;">{msg_body}</div>
                    <div style="font-size:11px; color:#00e5a3; margin-top:6px; font-weight:600;">Status: ✓ {d.get('status','Delivered')} via {d.get('provider','Direct Gateway').upper()}</div>
                </div>
                """, unsafe_allow_html=True)

        # 5. Send Encouragement Nudge from Parent Mobile
        st.markdown("### 💬 Send Instant Encouragement to Student Screen")
        n1, n2, n3 = st.columns(3)
        with n1:
            if st.button("👏 Keep going!", use_container_width=True):
                study_guard.send_parent_nudge("Parent", "Proud of you, keep up the great focus! 👏")
                st.toast("Encouragement sent to student screen!")
        with n2:
            if st.button("☕ Drink water!", use_container_width=True):
                study_guard.send_parent_nudge("Parent", "Remember to hydrate and take a deep breath! ☕")
                st.toast("Break reminder sent to student screen!")
        with n3:
            if st.button("🎯 Stay focused!", use_container_width=True):
                study_guard.send_parent_nudge("Parent", "Stay focused on your study goal! You got this! 🎯")
                st.toast("Focus nudge sent to student screen!")

    parent_live_monitor()

    st.divider()
    st.caption("FlowState Parent Mobile Portal • Connected via Local Network • Real-Time Biometric Study Monitor")
    if st.button("💻 Switch to Student Desktop View"):
        st.query_params.clear()
        st.rerun()
    st.stop()


# ==============================================================================
# ======================== STUDENT DESKTOP DASHBOARD ===========================
# ==============================================================================

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/brain.png", width=64)
    st.markdown("## ⏱️ Study Session Target")
    st.caption("Configure study sprint duration from **10 minutes** up to **5 hours**.")

    # Target Duration Presets
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        if st.button("🍅 25m (Pomodoro)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 25
            st.rerun()
        if st.button("🎯 60m (1 Hour)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 60
            st.rerun()
        if st.button("🚀 120m (2 Hours)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 120
            st.rerun()
    with p_col2:
        if st.button("📖 45m (Standard)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 45
            st.rerun()
        if st.button("⚡ 90m (Ultradian)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 90
            st.rerun()
        if st.button("🏆 300m (5 Hours)", use_container_width=True, disabled=st.session_state.active):
            st.session_state.target_minutes = 300
            st.rerun()

    # Continuous Slider from 10 to 300 minutes (10m to 5h)
    selected_mins = st.slider(
        "Session Duration (Minutes):",
        min_value=10,
        max_value=300,
        value=st.session_state.target_minutes,
        step=5,
        format="%d min",
        disabled=st.session_state.active,
        help="Choose any duration between 10 minutes and 5 hours (300 min)."
    )
    if selected_mins != st.session_state.target_minutes and not st.session_state.active:
        st.session_state.target_minutes = selected_mins

    hours = st.session_state.target_minutes // 60
    mins = st.session_state.target_minutes % 60
    duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"
    st.info(f"🎯 **Target Goal:** {duration_str}")

    st.divider()

    # ================= PARENT MOBILE NUMBER CONFIGURATION =================
    st.markdown("## 📱 Parent Mobile Details")
    parent_phone_input = st.text_input(
        "Parent Phone Number (with Country Code):",
        value=st.session_state.parent_phone,
        placeholder="+91 9876543210 or +1 2345678900",
        help="Enter parent's mobile phone number to enable 1-click WhatsApp alerts and study report sharing."
    )
    if parent_phone_input != st.session_state.parent_phone:
        st.session_state.parent_phone = parent_phone_input
        study_guard.update_shared_state({"parent_phone": parent_phone_input})

    # Direct Message Controls to Parent Number
    clean_p = re.sub(r'[^0-9]', '', st.session_state.parent_phone)
    if len(clean_p) >= 7:
        wa_invite_msg = (
            f"Hi Mom/Dad! I am starting a {duration_str} study session on FlowState.\n"
            f"You can monitor my live study progress here:\n"
            f"{parent_mobile_url}"
        )
        wa_invite_url = study_guard.format_whatsapp_url(st.session_state.parent_phone, wa_invite_msg)

        if st.button("🚀 Send Message Directly to Number", key="sidebar_direct_send_btn", use_container_width=True):
            res = study_guard.send_direct_message(st.session_state.parent_phone, wa_invite_msg, provider="auto")
            st.session_state.last_direct_dispatch_status = res
            st.toast(f"✅ Dispatched directly to {st.session_state.parent_phone}!")

        st.markdown(
            f'<a href="{wa_invite_url}" target="_blank" class="whatsapp-btn" style="text-align:center; display:block;">💬 Open in WhatsApp</a>',
            unsafe_allow_html=True,
        )

        st.markdown("**Automated Notifications:**")
        st.session_state.auto_alert_distraction = st.checkbox(
            "🔔 Alert on Prolonged Distraction (>30s)",
            value=st.session_state.auto_alert_distraction,
            help="Directly alerts parent phone if student gets distracted or watches passive entertainment."
        )
        st.session_state.auto_alert_completion = st.checkbox(
            "📋 Auto-Send Report on Finish",
            value=st.session_state.auto_alert_completion,
            help="Directly dispatches verified study performance summary when session ends."
        )

    st.divider()

    # ================= SMART APP BLOCKER SETTINGS =================
    st.markdown("## 🛡️ Focus Shield Mode")
    shield_options = {
        "Auto-Minimize (Recommended)": "minimize",
        "Strict Force-Close": "close",
        "Alert & Warn Only": "alert",
        "Disabled": "disabled"
    }
    shield_choice = st.selectbox(
        "Blocking Mode:",
        list(shield_options.keys()),
        index=0,
        disabled=st.session_state.active,
    )
    st.session_state.shield_mode = shield_options[shield_choice]

# Main Student Header (Minimal & Clean)
st.markdown(
    '<div class="security-banner">'
    '<span>🔒 100% LOCAL BIOMETRIC PROCESSING</span>'
    f'<span>📱 PARENT LINK: <a href="{parent_mobile_url}" target="_blank" style="color:#38bdf8; text-decoration:none;">OPEN MOBILE PORTAL</a></span>'
    '</div>',
    unsafe_allow_html=True,
)

st.title("🧠 FlowState StudyGuard")
st.caption("AI-driven distraction-free focus workspace.")

# Clean Session Control Bar
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.3, 1.3, 3])
with ctrl_col1:
    start = st.button("▶️ Start Study Session", use_container_width=True, disabled=st.session_state.active)
with ctrl_col2:
    stop = st.button("⏹️ Stop Session", use_container_width=True, disabled=not st.session_state.active)
with ctrl_col3:
    if not st.session_state.active:
        st.write(f"Target Duration: **{duration_str}** | Parent Mobile: **{st.session_state.parent_phone}**")

if start:
    if start_session():
        st.rerun()
    else:
        st.error("Could not open webcam. Close other camera apps and check Windows camera permissions.")

if stop:
    stop_session()
    st.rerun()

# ================= DYNAMIC LIVE STUDY SESSION (CLEAN MINIMAL SCREEN) =================
if st.session_state.active:
    @st.fragment(run_every=0.15)
    def live_study_monitor():
        if not st.session_state.active:
            return

        camera = st.session_state.camera
        if camera is None or not camera.isOpened():
            st.error("Webcam connection was lost.")
            stop_session()
            return

        ok, frame = camera.read()
        if not ok or frame is None:
            st.warning("Reading webcam frame...")
            return

        processed = process_frame(frame)

        # 1. CLEAN MINIMAL COUNTDOWN & SPRINT PROGRESS
        elapsed = elapsed_time()
        target = target_duration_seconds()
        remaining = remaining_time()
        prog = min(1.0, elapsed / target)
        prog_pct = int(prog * 100)
        countdown_clock = format_time(remaining)

        is_goal_met = elapsed >= target

        # Minimalist Sprint Header
        st.markdown(f"""
        <div style="background:#0c131d; border:2px solid {'#00e5a3' if not is_goal_met else '#f59e0b'}; border-radius:14px; padding:14px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:11px; font-weight:700; color:#8fa0b5; letter-spacing:1px; text-transform:uppercase;">
                    {'⏳ Study Countdown' if not is_goal_met else '🎉 Target Reached! Extra Study'}
                </div>
                <div style="font-size:32px; font-weight:900; color:{'#00e5a3' if not is_goal_met else '#fbbf24'}; font-family:'Segoe UI', monospace; letter-spacing:1px; margin-top:2px;">
                    {countdown_clock} <span style="font-size:14px; font-weight:600; color:#64748b;">LEFT</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:12px; font-weight:600; color:#94a3b8;">Goal: <b>{duration_str}</b> | Focus Score: <b style="color:#00e5a3;">{focus_score():.1f}%</b></div>
                <div style="font-size:18px; font-weight:800; color:#38bdf8; margin-top:2px;">{prog_pct}% COMPLETE</div>
            </div>
        </div>
        <div style="background:#17202e; border-radius:10px; height:10px; width:100%; overflow:hidden; border:1px solid #253346; margin-bottom:14px;">
            <div style="background:linear-gradient(90deg, #0284c7 0%, #00e5a3 100%); height:100%; width:{prog_pct}%;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Parent Encouragement Banner if sent
        latest_nudge = study_guard.get_latest_parent_nudge()
        if latest_nudge:
            st.markdown(f"""
            <div class="parent-nudge-card">
                <span>💌</span> <span><b>Message from Parent:</b> "{latest_nudge['message']}"</span>
            </div>
            """, unsafe_allow_html=True)

        # 2. MAIN CLEAN VIDEO FOCUS MONITOR (CENTERED & UNCLUTTERED)
        st.image(
            cv2.cvtColor(processed, cv2.COLOR_BGR2RGB),
            channels="RGB",
            use_container_width=True,
        )

        st.divider()

        # ================= HIDDEN OPTIONS & DIAGNOSTICS =================
        tele = st.session_state.latest_telemetry

        # OPTION 1: 🔍 Multi-Modal Signals & Biometrics (Hidden inside expander)
        with st.expander("🔍 Advanced Signals & AI Biometrics (Click to Expand)", expanded=False):
            b1, b2, b3 = st.columns(3)
            with b1:
                st.markdown(f"""
                <div class="telemetry-card">
                    <div class="telemetry-label">Active Window & Process</div>
                    <div style="font-weight:700; color:#e2e8f0;">{tele.get('proc_name', 'unknown')}</div>
                    <div style="font-size:12px; color:#94a3b8;">{tele.get('win_title', 'Unknown')}</div>
                    <div style="margin-top:4px; font-size:12px;">Classification: <b>{tele.get('app_cat', 'NEUTRAL')}</b></div>
                </div>
                """, unsafe_allow_html=True)
            with b2:
                idle_sec = tele.get("idle_sec", 0.0)
                bpm = tele.get("bpm", 0.0)
                is_reading = tele.get("is_reading", False)
                st.markdown(f"""
                <div class="telemetry-card">
                    <div class="telemetry-label">Peripheral & Eye Dynamics</div>
                    <div><b>Keyboard/Mouse Idle:</b> {int(idle_sec)}s</div>
                    <div><b>Blink Frequency:</b> {bpm:.0f} blinks/min</div>
                    <div><b>Eye Pattern:</b> {'Reading Saccades' if is_reading else 'Screen Gaze'}</div>
                </div>
                """, unsafe_allow_html=True)
            with b3:
                flash_rmsd = tele.get("flash_rmsd", 0.0)
                st.markdown(f"""
                <div class="telemetry-card">
                    <div class="telemetry-label">Ambient Screen Glare (Movies/Games)</div>
                    <div><b>Glare Flux:</b> {'Dynamic Video/Game' if flash_rmsd > 3.8 else 'Steady Study Light'}</div>
                    <div style="font-size:12px; color:#94a3b8;">Luminance Volatility: {flash_rmsd:.2f} RMSD</div>
                </div>
                """, unsafe_allow_html=True)

        # OPTION 2: 🛡️ Focus Shield & Distraction Block Log (Hidden inside expander)
        with st.expander(f"🛡️ Distraction Shield & Interception Log ({st.session_state.guard.shield.total_blocked_count} Blocked)", expanded=False):
            history = st.session_state.guard.shield.blocked_history
            if history:
                for item in history[:8]:
                    st.markdown(f"""
                    <div style="background:rgba(255,60,60,0.08); border-left:3px solid #ff4d4d; padding:6px 12px; margin-bottom:6px; font-size:13px;">
                        `{item['timestamp']}` - Blocked <b>{item['app']}</b> ({item['action']}) ➜ <i>{item.get('reason','Distraction')}</i>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No distractions intercepted yet. Focus Shield is active.")

        # OPTION 3: 📱 Parent Mobile Connection & Direct Messaging (Hidden inside expander)
        with st.expander("📱 Parent Mobile Connection & Direct Messaging", expanded=False):
            q_col1, q_col2 = st.columns([1, 2])
            with q_col1:
                if parent_qr_b64:
                    st.markdown(f"""
                    <div style="text-align:center; background:#0c131d; padding:10px; border-radius:10px; border:1px solid #1e293b;">
                        <img src="data:image/png;base64,{parent_qr_b64}" width="140" style="border-radius:8px;" />
                        <div style="font-size:11px; color:#00e5a3; font-weight:700; margin-top:6px;">Scan with Parent Phone</div>
                    </div>
                    """, unsafe_allow_html=True)
            with q_col2:
                st.write(f"**Parent Mobile Number:** `{st.session_state.parent_phone}`")
                st.write(f"**Live Dashboard URL:** `{parent_mobile_url}`")
                if len(clean_p) >= 7:
                    d_c1, d_c2 = st.columns([1.2, 1])
                    with d_c1:
                        if st.button("🚀 Send Link Directly to Number", key="expander_direct_send", use_container_width=True):
                            res = study_guard.send_direct_message(st.session_state.parent_phone, wa_invite_msg, provider="auto")
                            st.session_state.last_direct_dispatch_status = res
                            st.toast(f"✅ Dispatched directly to {st.session_state.parent_phone}!")
                    with d_c2:
                        st.markdown(
                            f'<a href="{wa_invite_url}" target="_blank" class="whatsapp-btn" style="text-align:center; display:block;">💬 Open WhatsApp</a>',
                            unsafe_allow_html=True,
                        )
                st.caption("Parents can watch the live session progress and receive instant direct alerts on their phone.")

            # Custom Quick Message Direct Dispatch
            if len(clean_p) >= 7:
                st.markdown("---")
                st.markdown("##### ✉️ Quick Direct Message to Parent Mobile")
                quick_preset = st.selectbox(
                    "Choose Message Preset or Custom:",
                    [
                        "🟢 Everything is on track! Full focus maintained.",
                        "⚠️ Break time - pausing for 5 minutes of rest.",
                        "🎯 Reached 50% of today's study target!",
                        "✍️ Custom message..."
                    ],
                    key="quick_msg_preset_active"
                )
                custom_txt = ""
                if "Custom" in quick_preset:
                    custom_txt = st.text_input("Enter custom message:", placeholder="e.g. Completed Chapter 4 math questions!", key="custom_msg_active_input")
                msg_to_send = custom_txt if ("Custom" in quick_preset and custom_txt.strip()) else quick_preset

                if st.button("📤 Send Direct Message to Phone", key="send_custom_quick_active"):
                    res = study_guard.send_direct_message(st.session_state.parent_phone, msg_to_send, provider="auto")
                    st.success(f"✅ Dispatched directly to {st.session_state.parent_phone} via {res.get('provider','Direct Gateway').upper()}!")

    live_study_monitor()

# ================= FINAL SESSION SUMMARY =================
if st.session_state.final_summary is not None:
    summary = st.session_state.final_summary
    st.divider()
    st.subheader("📊 Study Session Performance Report")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Session Time", format_time(summary["elapsed"]))
    with s2:
        st.metric("Target Goal", f'{summary["target_mins"]} min')
    with s3:
        st.metric("Focus Score", f'{summary["score"]:.1f}%')
    with s4:
        st.metric("Total Deep Focus", format_time(summary["focused"]))

    st.markdown("### 🔍 Study Breakdown")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("📖 Reading & Study Time", format_time(summary["reading"]))
    with b2:
        st.metric("🎬 Passive Media Flags", f'{summary["passive_incidents"]} flags')
    with b3:
        st.metric("🚫 Distractions Blocked", f'{summary["total_blocked_apps"]} apps')

    # WhatsApp Report Share to Parent
    parent_num = summary.get("parent_phone", "").strip()
    share_msg = (
        f"*FlowState Study Report:*\n"
        f"🎯 Target Goal: {summary['target_mins']} mins\n"
        f"⏱️ Total Study Time: {format_time(summary['elapsed'])}\n"
        f"🧠 Focus Score: {summary['score']:.1f}%\n"
        f"📖 Deep Focus: {format_time(summary['focused'])}\n"
        f"🛡️ Distractions Blocked: {summary['total_blocked_apps']}\n"
        f"Verified by FlowState StudyGuard AI."
    )
    wa_report_url = study_guard.format_whatsapp_url(parent_num, share_msg)

    st.markdown("### 📲 Send Report Directly to Parent Mobile")
    clean_p_num = re.sub(r'[^0-9]', '', parent_num)
    if parent_num and len(clean_p_num) >= 7:
        d_col1, d_col2 = st.columns([1.5, 1])
        with d_col1:
            if st.button(f"🚀 Send Report Directly to {parent_num}", key="direct_send_final_report_btn", type="primary", use_container_width=True):
                res = study_guard.send_direct_message(parent_num, share_msg, provider="auto")
                st.session_state.last_direct_dispatch_status = res
                st.success(f"✅ Verified Study Report dispatched directly to {parent_num} via {res.get('provider','Direct Gateway').upper()}!")
        with d_col2:
            if wa_report_url:
                st.markdown(
                    f'<a href="{wa_report_url}" target="_blank" class="whatsapp-btn" style="text-align:center; display:block;">💬 Open in WhatsApp</a>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Enter Parent's Mobile Number in the sidebar to send direct study reports.")

    with st.expander("📄 View Text Report Format"):
        st.code(share_msg, language="markdown")

    st.success("Session completed and resources safely released.")

elif not st.session_state.active:
    st.info(f"Target session set to **{duration_str}**. Press **Start Study Session** to begin.")
    # Show Collapsed Options when idle
    with st.expander("📱 Parent Mobile Connect & QR Code", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            if parent_qr_b64:
                st.markdown(f"""
                <div style="text-align:center; background:#0c131d; padding:10px; border-radius:10px; border:1px solid #1e293b;">
                    <img src="data:image/png;base64,{parent_qr_b64}" width="150" style="border-radius:8px;" />
                    <div style="font-size:11px; color:#00e5a3; font-weight:700; margin-top:6px;">Scan with Parent Phone</div>
                </div>
                """, unsafe_allow_html=True)
        with c2:
            st.write(f"**Parent Mobile Number:** `{st.session_state.parent_phone}`")
            st.write(f"**Live Dashboard URL:** `{parent_mobile_url}`")
            clean_p = re.sub(r'[^0-9]', '', st.session_state.parent_phone)
            if len(clean_p) >= 7:
                wa_msg = f"Hi Mom/Dad! Here is the link to my FlowState study dashboard:\n{parent_mobile_url}"
                wa_url = study_guard.format_whatsapp_url(st.session_state.parent_phone, wa_msg)

                d_c1, d_c2 = st.columns([1.2, 1])
                with d_c1:
                    if st.button("🚀 Send Message Directly to Number", key="idle_direct_send_btn", use_container_width=True):
                        res = study_guard.send_direct_message(st.session_state.parent_phone, wa_msg, provider="auto")
                        st.session_state.last_direct_dispatch_status = res
                        st.toast(f"✅ Dispatched directly to {st.session_state.parent_phone}!")
                with d_c2:
                    st.markdown(
                        f'<a href="{wa_url}" target="_blank" class="whatsapp-btn" style="text-align:center; display:block;">💬 Open WhatsApp</a>',
                        unsafe_allow_html=True,
                    )
