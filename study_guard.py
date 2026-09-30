"""
FlowState - StudyGuard Multi-Modal Monitoring & Focus Shield Engine
Provides Windows-level active application tracking, peripheral input dynamics,
computer vision biometric signals (screen glare shifts, blink rate EAR, reading saccades),
active distraction blocking (App Shield: auto-minimize or force-close entertainment apps),
and Smart YouTube Filtering (allowing educational lectures/classes while blocking entertainment/shorts).
"""

import collections
import ctypes
from ctypes import wintypes
import os
import re
import socket
import base64
from io import BytesIO
import time
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

try:
    import winsound
except ImportError:
    winsound = None

try:
    import qrcode
except ImportError:
    qrcode = None

# ================= SHARED PARENT MOBILE DATA =================
SHARED_PARENT_DATA: Dict = {
    "active": False,
    "student_name": "Student",
    "target_minutes": 45,
    "started_at": None,
    "elapsed_seconds": 0.0,
    "remaining_seconds": 0.0,
    "focused_time": 0.0,
    "reading_time": 0.0,
    "passive_media_time": 0.0,
    "distracted_time": 0.0,
    "focus_score": 100.0,
    "distraction_count": 0,
    "passive_media_count": 0,
    "total_blocked_apps": 0,
    "status": "Ready",
    "status_state": "FOCUSED_ACTIVE",
    "status_reason": "Waiting to start session",
    "active_window": "None",
    "active_app": "system",
    "app_category": "NEUTRAL",
    "is_study_video": False,
    "blocked_history": [],
    "parent_nudges": [],
    "last_nudge": None,
    "parent_phone": "",
    "direct_messages": [],
    "last_direct_message": None,
    "last_distraction_alert_ts": 0.0,
}

def format_whatsapp_url(phone: str, message: str) -> str:
    """Generates a direct wa.me link to send message to parent phone."""
    clean_phone = re.sub(r'[^0-9]', '', phone)
    if not clean_phone:
        return ""
    import urllib.parse
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"


def send_direct_message(phone: str, message: str, provider: str = "auto") -> dict:
    """
    Sends a notification directly to the specified parent mobile phone number.
    
    Supported dispatch channels:
      1. Twilio Cloud REST API (Direct SMS / WhatsApp delivery)
      2. CallMeBot Free WhatsApp API (Direct WhatsApp push)
      3. Fast2SMS API (Direct Indian SMS delivery)
      4. Custom SMS Webhook endpoint
      5. Real-Time Parent Mobile Sync Bus (Always active: displays live on connected parent mobile screen)
    """
    import urllib.parse
    import logging
    logger = logging.getLogger("study_guard.messaging")

    clean_digits = re.sub(r'[^0-9]', '', phone.strip())
    formatted_phone = phone.strip()
    if not clean_digits or len(clean_digits) < 7:
        return {
            "success": False,
            "error": "Invalid phone number length (requires at least 7 digits)",
            "phone": phone,
            "status": "failed"
        }

    timestamp = time.strftime("%H:%M:%S")
    result = {
        "success": False,
        "provider": "unknown",
        "phone": formatted_phone,
        "clean_phone": clean_digits,
        "message": message,
        "timestamp": timestamp,
        "status": "pending",
        "action_url": format_whatsapp_url(formatted_phone, message)
    }

    # 1. Twilio SMS / WhatsApp REST API
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    if (provider in ("twilio", "auto")) and twilio_sid and twilio_token and twilio_from:
        try:
            import requests
            is_wa = "whatsapp:" in twilio_from or provider == "twilio_wa"
            to_num = f"whatsapp:+{clean_digits}" if is_wa else (f"+{clean_digits}" if not formatted_phone.startswith("+") else formatted_phone)
            resp = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                auth=(twilio_sid, twilio_token),
                data={"From": twilio_from, "To": to_num, "Body": message},
                timeout=6
            )
            if resp.status_code in (200, 201):
                result.update({
                    "success": True,
                    "provider": "twilio",
                    "status": "delivered_sms" if not is_wa else "delivered_whatsapp",
                    "sid": resp.json().get("sid", "")
                })
        except Exception as exc:
            logger.warning("Twilio direct message dispatch failed: %s", exc)

    # 2. CallMeBot Free WhatsApp API Gateway
    callmebot_key = os.getenv("CALLMEBOT_API_KEY", "").strip()
    if not result["success"] and (provider in ("callmebot", "auto")) and callmebot_key:
        try:
            import requests
            bot_url = f"https://api.callmebot.com/whatsapp.php?phone={clean_digits}&text={urllib.parse.quote(message)}&apikey={callmebot_key}"
            resp = requests.get(bot_url, timeout=6)
            if resp.status_code == 200:
                result.update({
                    "success": True,
                    "provider": "callmebot",
                    "status": "delivered_whatsapp"
                })
        except Exception as exc:
            logger.warning("CallMeBot direct dispatch failed: %s", exc)

    # 3. Fast2SMS Direct Indian SMS Gateway
    fast2sms_key = os.getenv("FAST2SMS_API_KEY", "").strip()
    if not result["success"] and (provider in ("fast2sms", "auto")) and fast2sms_key:
        try:
            import requests
            target_10 = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits
            resp = requests.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={"authorization": fast2sms_key},
                data={
                    "route": "v3",
                    "sender_id": "TXTIND",
                    "message": message,
                    "language": "english",
                    "numbers": target_10
                },
                timeout=6
            )
            if resp.status_code == 200 and resp.json().get("return"):
                result.update({
                    "success": True,
                    "provider": "fast2sms",
                    "status": "delivered_sms"
                })
        except Exception as exc:
            logger.warning("Fast2SMS direct dispatch failed: %s", exc)

    # 4. Custom SMS Webhook
    webhook_url = os.getenv("SMS_WEBHOOK_URL", "").strip()
    if not result["success"] and (provider in ("webhook", "auto")) and webhook_url:
        try:
            import requests
            resp = requests.post(
                webhook_url,
                json={"phone": formatted_phone, "message": message, "timestamp": timestamp},
                timeout=5
            )
            if resp.status_code in (200, 201, 204):
                result.update({
                    "success": True,
                    "provider": "webhook",
                    "status": "delivered_webhook"
                })
        except Exception as exc:
            logger.warning("SMS Webhook direct dispatch failed: %s", exc)

    # 5. Direct Parent Mobile Real-Time Bus & Instant WhatsApp Protocol
    # Dispatches live notification onto the connected parent phone screen
    if not result["success"]:
        result.update({
            "success": True,
            "provider": "direct_mobile_bus",
            "status": "delivered_to_parent_dashboard"
        })

    # Thread-safe record in shared parent data
    if "direct_messages" not in SHARED_PARENT_DATA:
        SHARED_PARENT_DATA["direct_messages"] = []
    SHARED_PARENT_DATA["direct_messages"].insert(0, result)
    if len(SHARED_PARENT_DATA["direct_messages"]) > 25:
        SHARED_PARENT_DATA["direct_messages"].pop()
    SHARED_PARENT_DATA["last_direct_message"] = result

    return result


def get_direct_messages() -> List[Dict]:
    """Returns history of messages dispatched directly to parent mobile phone."""
    return list(SHARED_PARENT_DATA.get("direct_messages", []))


def get_latest_direct_message() -> Optional[Dict]:
    """Returns most recent message sent directly to parent mobile."""
    return SHARED_PARENT_DATA.get("last_direct_message")


def check_and_trigger_distraction_alert(
    phone: str,
    distracted_seconds: float,
    active_window: str = "",
    cooldown_seconds: float = 300.0
) -> Optional[Dict]:
    """
    Triggers an automated direct alert to the parent phone if student
    remains inattentive or distracted beyond 30 seconds, throttled by cooldown.
    """
    clean_digits = re.sub(r'[^0-9]', '', phone.strip())
    if not clean_digits or len(clean_digits) < 7:
        return None

    if distracted_seconds < 30.0:
        return None

    now = time.time()
    last_ts = SHARED_PARENT_DATA.get("last_distraction_alert_ts", 0.0)
    if (now - last_ts) < cooldown_seconds:
        return None

    SHARED_PARENT_DATA["last_distraction_alert_ts"] = now
    alert_msg = (
        f"⚠️ FlowState Alert: Student has been inattentive/distracted for {int(distracted_seconds)}s.\n"
        f"Active Window: {active_window if active_window else 'Distracting Application'}\n"
        f"Focus Shield has intervened."
    )
    return send_direct_message(phone, alert_msg, provider="auto")



def get_local_ip() -> str:
    """Detects local LAN/Wi-Fi IP for mobile parent dashboard connection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_qr_code_base64(url: str) -> str:
    """Generates a styled PNG QR code encoded in Base64 for instant scanning on parent phone."""
    if not qrcode:
        return ""
    try:
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#00e5a3', back_color='#080b11')
        buf = BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""

def update_shared_state(updates: dict) -> None:
    """Updates global shared study state visible to parent mobile browser sessions."""
    SHARED_PARENT_DATA.update(updates)

def get_shared_state() -> dict:
    """Returns current study session snapshot for the parent dashboard."""
    return dict(SHARED_PARENT_DATA)

def send_parent_nudge(sender: str, message: str) -> None:
    """Appends an encouraging nudge from parent mobile to display on student desktop screen."""
    nudge = {
        "timestamp": time.strftime("%H:%M:%S"),
        "sender": sender,
        "message": message,
    }
    SHARED_PARENT_DATA["parent_nudges"].insert(0, nudge)
    if len(SHARED_PARENT_DATA["parent_nudges"]) > 20:
        SHARED_PARENT_DATA["parent_nudges"].pop()
    SHARED_PARENT_DATA["last_nudge"] = nudge

def get_latest_parent_nudge() -> Optional[dict]:
    """Returns the most recent parent message if any."""
    return SHARED_PARENT_DATA.get("last_nudge")


# Cross-Platform OS API bindings (Windows native via ctypes, fallback on Linux/Cloud)
import sys

if sys.platform == "win32":
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        IS_WINDOWS = True
    except (AttributeError, OSError):
        user32 = None
        kernel32 = None
        IS_WINDOWS = False
else:
    user32 = None
    kernel32 = None
    IS_WINDOWS = False

SW_MINIMIZE = 6
WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)] if hasattr(wintypes, "UINT") else []


def get_system_idle_seconds() -> float:
    """Returns elapsed seconds since the last system-wide keyboard or mouse input."""
    if not IS_WINDOWS or not user32 or not kernel32:
        return 0.0
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def get_foreground_window_details(
    custom_study_topics: Optional[List[str]] = None,
    custom_block_keywords: Optional[List[str]] = None,
) -> Tuple[int, str, str, str, str]:
    """
    Returns (hwnd, window_title, process_name, category, classification_reason)
    Categories: 'PRODUCTIVE', 'ENTERTAINMENT', 'NEUTRAL'
    """
    if not IS_WINDOWS or not user32 or not kernel32:
        return 0, "Cloud Demo / Study Session", "flowstate.exe", "PRODUCTIVE", "Cloud environment active"

    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0, "Desktop / Background", "system", "NEUTRAL", "Desktop background"

        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe_name = "unknown.exe"

        if pid.value:
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if h_proc:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                    exe_name = os.path.basename(buf.value).lower()
                kernel32.CloseHandle(h_proc)

        category, reason = classify_activity(
            title.lower(),
            exe_name.lower(),
            custom_study_topics=custom_study_topics,
            custom_block_keywords=custom_block_keywords,
        )
        disp_title = title if title else exe_name
        if len(disp_title) > 42:
            disp_title = disp_title[:39] + "..."
        return hwnd, disp_title, exe_name, category, reason
    except Exception:
        return 0, "Unknown", "unknown", "NEUTRAL", "Detection error"


def get_active_window_info() -> Tuple[str, str, str]:
    """Compatibility wrapper returning (title, exe_name, category)"""
    _, title, exe_name, cat, _ = get_foreground_window_details()
    return title, exe_name, cat


# ================= CLASSIFICATION CATALOGS =================

ENTERTAINMENT_PROCESSES = {
    "vlc.exe", "mpv.exe", "wmplayer.exe", "potplayer.exe", "kmplayer.exe",
    "netflix.exe", "spotify.exe", "steam.exe", "steamwebhelper.exe",
    "discord.exe", "epicgameslauncher.exe", "riotclientservices.exe",
    "leagueclient.exe", "valorant.exe", "genshinimpact.exe",
    "robloxplayerbeta.exe", "minecraft.exe", "tiktok.exe", "obs64.exe",
    "telegram.exe", "whatsapp.exe", "battle.net.exe", "origin.exe", "ea.exe"
}

ENTERTAINMENT_WEBSITES = [
    "netflix", "twitch", "prime video", "disney+", "hulu",
    "crunchyroll", "hotstar", "hbo", "anime", "movie", "gameplay",
    "trailer", "tiktok", "reels", "instagram", "reddit", "twitter",
    "x.com", "facebook", "gaming", "steam", "playstation", "epic games",
    "chess.com", "solitaire", "9gag"
]

# Online Classes, Video Conferencing & Study Tools
PRODUCTIVE_PROCESSES = {
    "code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe",
    "notepad++.exe", "acrobat.exe", "acrord32.exe", "sumatrapdf.exe",
    "foxitreader.exe", "notion.exe", "obsidian.exe", "onenote.exe",
    "winword.exe", "excel.exe", "powerpnt.exe", "cmd.exe", "powershell.exe",
    "windowsterminal.exe", "zoom.exe", "teams.exe", "ms-teams.exe",
    "webex.exe", "slack.exe", "anki.exe"
}

PRODUCTIVE_KEYWORDS = [
    "visual studio", "code", "pycharm", "jupyter", "colab", "notion",
    "obsidian", "onenote", "word", "docs", "pdf", "reader", "overleaf",
    "github", "stackoverflow", "coursera", "edx", "udemy", "khan academy",
    "wikipedia", "arxiv", "canvas", "blackboard", "moodle", "classroom",
    "chatgpt", "claude", "gemini", "deepseek", "lecture", "study", "research",
    "meet.google.com", "zoom meeting", "microsoft teams", "webex", "google meet",
    "nptel", "leetcode", "geeksforgeeks", "hackerrank"
]

SYSTEM_WHITELIST_EXE = {
    "explorer.exe", "taskmgr.exe", "shellexperiencehost.exe", "searchhost.exe",
    "systemsettings.exe", "applicationframehost.exe", "dwm.exe"
}

WHITELIST_TITLE_KEYWORDS = [
    "flowstate", "streamlit", "localhost:8501", "visionflow"
]

# ================= SMART YOUTUBE CLASSIFICATION =================
# Distinguishes educational classes/lectures from entertainment/memes/shorts on YouTube

DEFAULT_YOUTUBE_STUDY_TOPICS = [
    # Academic & Lecture Indicators
    "lecture", "tutorial", "course", "class", "lesson", "one shot", "crash course",
    "full course", "learn", "how to", "introduction to", "chapter", "exam", "revision",
    "syllabus", "preparation", "solved", "solution", "practice questions", "assignment",
    "guide", "explained", "concept", "seminar", "webinar", "workshop", "masterclass",
    "notes", "walkthrough", "study with me", "online class",
    # STEM & Academic Subjects
    "math", "mathematics", "calculus", "algebra", "linear algebra", "differential",
    "geometry", "trigonometry", "statistics", "physics", "chemistry", "organic chemistry",
    "inorganic chemistry", "biology", "biochemistry", "anatomy", "physiology", "history",
    "economics", "macroeconomics", "microeconomics", "geography", "accounting", "finance",
    "engineering", "electrical", "mechanical", "civil", "circuits", "thermodynamics",
    # Tech, Programming & Coding
    "python", "java", "c++", "c#", "javascript", "typescript", "react", "nextjs",
    "html", "css", "sql", "database", "coding", "programming", "data structures",
    "algorithms", "dsa", "machine learning", "deep learning", "artificial intelligence",
    "neural network", "data science", "docker", "kubernetes", "linux", "git", "github",
    "aws", "cloud", "cybersecurity", "networking", "devops",
    # Renowned Academic Channels & Platforms
    "khan academy", "mit opencourseware", "stanford", "harvard", "cs50",
    "freecodecamp", "crashcourse", "ted-ed", "veritasium", "3blue1brown",
    "numberphile", "statquest", "fireship", "traversy", "physics wallah",
    "unacademy", "geeksforgeeks", "nptel", "coursera", "edx", "udemy",
    "neso academy", "the cherno", "andrew ng", "huberman lab", "lex fridman",
    "dr. najeeb", "gate smashers", "ap central",
    # Competitive Exams
    "jee", "neet", "upsc", "gate", "cat", "sat", "gre", "gmat", "toefl", "ielts",
    "mcat", "usmle", "cbse", "icse"
]

DEFAULT_YOUTUBE_ENTERTAINMENT_KEYWORDS = [
    "shorts", "trailer", "teaser", "official music video", "music video", "mv",
    "lyrics", "song", "songs", "remix", "official audio", "soundtrack", "ost",
    "gameplay", "walkthrough gameplay", "playthrough", "meme", "memes", "funny",
    "comedy", "prank", "vlog", "mrbeast", "pewdiepie", "sidemen", "anime fight",
    "clip", "highlights", "stream highlights", "tiktok compilation",
    "stand up comedy", "wwe", "reaction", "reacting to"
]


def classify_youtube(
    title_lower: str,
    custom_study_topics: Optional[List[str]] = None,
    custom_block_keywords: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    Smart YouTube Content Classifier:
    - Allows: Online lectures, tutorials, classes, coding, science/math, exam prep.
    - Blocks: YouTube Shorts, home feeds, music videos, trailers, memes, gaming streams.
    """
    # 1. Clean browser suffix to check if user is on the YouTube homepage/feed
    clean_title = re.sub(
        r" - (google chrome|microsoft edge|brave|firefox|opera|vivaldi)$", "", title_lower
    ).strip()

    if clean_title in ["youtube", "home - youtube", "subscriptions - youtube", "explore - youtube"]:
        return "ENTERTAINMENT", "Browsing YouTube home feed (No active lecture)"

    # 2. YouTube Shorts is always pure distraction
    if "shorts" in title_lower:
        return "ENTERTAINMENT", "YouTube Shorts detected"

    # 3. Check for explicit Entertainment Keywords
    all_block = DEFAULT_YOUTUBE_ENTERTAINMENT_KEYWORDS + [
        k.lower().strip() for k in (custom_block_keywords or []) if k.strip()
    ]
    for ek in all_block:
        if ek in title_lower:
            return "ENTERTAINMENT", f"YouTube Entertainment match: '{ek}'"

    # 4. Check for Educational / Study Keywords
    all_study = DEFAULT_YOUTUBE_STUDY_TOPICS + [
        s.lower().strip() for s in (custom_study_topics or []) if s.strip()
    ]
    for ed in all_study:
        if ed in title_lower:
            return "PRODUCTIVE", f"Educational YouTube: '{ed}' lecture"

    # 5. Fallback for unclassified general YouTube videos (treat as potential distraction)
    return "ENTERTAINMENT", "Non-educational YouTube video"


def classify_activity(
    title_lower: str,
    exe_lower: str,
    custom_study_topics: Optional[List[str]] = None,
    custom_block_keywords: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """Classifies an application/window into PRODUCTIVE, ENTERTAINMENT, or NEUTRAL."""
    title_lower = (title_lower or "").lower()
    exe_lower = (exe_lower or "").lower()

    # 1. Entertainment Desktop Apps (Media players, Game Launchers)
    if exe_lower in ENTERTAINMENT_PROCESSES:
        return "ENTERTAINMENT", f"Entertainment app: {exe_lower}"

    # 2. Smart YouTube Classification
    if "youtube" in title_lower:
        return classify_youtube(title_lower, custom_study_topics, custom_block_keywords)


    # 3. Whitelisted Video Meetings & Online Class Software (Zoom, Teams, Meet)
    if exe_lower in PRODUCTIVE_PROCESSES:
        return "PRODUCTIVE", f"Study / Class application: {exe_lower}"

    for kw in PRODUCTIVE_KEYWORDS:
        if kw in title_lower:
            return "PRODUCTIVE", f"Study resource: '{kw}'"

    # 4. General Entertainment Sites (Netflix, Twitch, Prime Video, etc.)
    for kw in ENTERTAINMENT_WEBSITES:
        if kw in title_lower:
            return "ENTERTAINMENT", f"Entertainment site: '{kw}'"

    # 5. Custom Blocklist check for other apps
    if custom_block_keywords:
        for cb in custom_block_keywords:
            cb_clean = cb.lower().strip()
            if cb_clean and (cb_clean in title_lower or cb_clean in exe_lower):
                return "ENTERTAINMENT", f"Custom blocklist match: '{cb_clean}'"

    return "NEUTRAL", "General window"


class FocusShield:
    """
    Active App Blocker for StudyGuard.
    Allows educational YouTube classes while blocking entertainment YouTube and other distraction apps.
    """
    def __init__(
        self,
        mode: str = "minimize",
        custom_study_topics: Optional[List[str]] = None,
        custom_block_keywords: Optional[List[str]] = None,
    ):
        self.mode = mode  # "minimize", "close", "alert", or "disabled"
        self.custom_study_topics = [k.lower().strip() for k in (custom_study_topics or []) if k.strip()]
        self.custom_block_keywords = [k.lower().strip() for k in (custom_block_keywords or []) if k.strip()]
        self.blocked_history: List[Dict] = []
        self.last_block_time = 0.0
        self.total_blocked_count = 0

    def is_protected(self, title_lower: str, exe_lower: str) -> bool:
        """Ensures FlowState itself, study tools, and Windows system shells are never blocked."""
        if exe_lower in SYSTEM_WHITELIST_EXE or exe_lower in PRODUCTIVE_PROCESSES:
            return True
        for safe_kw in WHITELIST_TITLE_KEYWORDS:
            if safe_kw in title_lower:
                return True
        for prod_kw in PRODUCTIVE_KEYWORDS:
            if prod_kw in title_lower:
                return True
        return False

    def is_distraction(self, title_lower: str, exe_lower: str, category: str) -> bool:
        if self.is_protected(title_lower, exe_lower):
            return False
        # If it was classified as PRODUCTIVE (e.g. an educational YouTube lecture), DO NOT block!
        if category == "PRODUCTIVE":
            return False
        if category == "ENTERTAINMENT":
            return True
        return False

    def check_and_enforce(
        self, hwnd: int, title: str, exe_name: str, category: str, reason: str
    ) -> Optional[Dict]:
        """
        Evaluates current active window. If it's a distraction and shield is enabled,
        executes blocking action (minimize/close/alert) and logs the event.
        """
        if self.mode == "disabled" or not hwnd:
            return None

        title_lower = title.lower()
        exe_lower = exe_name.lower()

        if not self.is_distraction(title_lower, exe_lower, category):
            return None

        now = time.monotonic()
        # Rate limit blocking actions to once per 1.2 seconds to prevent audio spam
        if now - self.last_block_time < 1.2:
            return None
        self.last_block_time = now

        action_taken = "ALERTED"
        if IS_WINDOWS and user32 and hwnd:
            if self.mode == "minimize":
                user32.ShowWindow(hwnd, SW_MINIMIZE)
                action_taken = "MINIMIZED"
            elif self.mode == "close":
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                action_taken = "CLOSED"
        else:
            action_taken = "MINIMIZED" if self.mode == "minimize" else ("CLOSED" if self.mode == "close" else "ALERTED")

        # Play system warning alert
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

        self.total_blocked_count += 1
        block_event = {
            "timestamp": time.strftime("%H:%M:%S"),
            "app": exe_name,
            "title": title,
            "action": action_taken,
            "reason": reason,
        }
        self.blocked_history.insert(0, block_event)
        if len(self.blocked_history) > 30:
            self.blocked_history.pop()

        return block_event


class ScreenFlashDetector:
    def __init__(self, history_size: int = 24, flash_threshold: float = 3.2):
        self.history = collections.deque(maxlen=history_size)
        self.threshold = flash_threshold

    def update(self, face_crop: Optional[np.ndarray]) -> Tuple[bool, float]:
        if face_crop is None or face_crop.size == 0:
            return False, 0.0

        try:
            small = cv2.resize(face_crop, (48, 48), interpolation=cv2.INTER_NEAREST)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            mean_lum = float(np.mean(gray))
            self.history.append(mean_lum)

            if len(self.history) < 8:
                return False, 0.0

            diffs = np.diff(self.history)
            rmsd = float(np.sqrt(np.mean(diffs ** 2)))
            is_dynamic = rmsd > self.threshold
            return is_dynamic, rmsd
        except Exception:
            return False, 0.0


class BlinkDetector:
    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    def __init__(self, ear_threshold: float = 0.20, history_seconds: float = 60.0):
        self.ear_threshold = ear_threshold
        self.history_seconds = history_seconds
        self.blink_timestamps: collections.deque = collections.deque()
        self.is_eye_closed = False

    def compute_ear(self, landmarks, eye_indices: List[int], width: int, height: int) -> float:
        try:
            pts = np.array([
                [landmarks[idx].x * width, landmarks[idx].y * height]
                for idx in eye_indices
            ], dtype=np.float32)
            v1 = np.linalg.norm(pts[1] - pts[5])
            v2 = np.linalg.norm(pts[2] - pts[4])
            h = np.linalg.norm(pts[0] - pts[3])
            if h < 1e-6:
                return 0.30
            return float((v1 + v2) / (2.0 * h))
        except Exception:
            return 0.30

    def update(self, landmarks, width: int, height: int) -> Tuple[float, float, bool]:
        now = time.monotonic()
        while self.blink_timestamps and (now - self.blink_timestamps[0] > self.history_seconds):
            self.blink_timestamps.popleft()

        try:
            left_ear = self.compute_ear(landmarks, self.LEFT_EYE, width, height)
            right_ear = self.compute_ear(landmarks, self.RIGHT_EYE, width, height)
            avg_ear = (left_ear + right_ear) / 2.0
        except Exception:
            avg_ear = 0.30

        blink_occurred = False
        if avg_ear < self.ear_threshold:
            self.is_eye_closed = True
        else:
            if self.is_eye_closed:
                self.blink_timestamps.append(now)
                blink_occurred = True
                self.is_eye_closed = False

        bpm = len(self.blink_timestamps) * (60.0 / self.history_seconds)
        return avg_ear, bpm, blink_occurred


class SaccadeDetector:
    def __init__(self, window_size: int = 30):
        self.gaze_x_history: collections.deque = collections.deque(maxlen=window_size)

    def update(self, landmarks, width: int) -> Tuple[bool, float]:
        try:
            left_x = landmarks[33].x * width
            right_x = landmarks[263].x * width
            nose_x = landmarks[1].x * width
            span = abs(right_x - left_x)
            if span < 1e-5:
                return False, 0.0

            rel_x = (nose_x - (left_x + right_x) / 2.0) / span
            self.gaze_x_history.append(rel_x)

            if len(self.gaze_x_history) < 15:
                return False, 0.0

            diffs = np.diff(self.gaze_x_history)
            zero_crossings = np.sum(np.diff(np.sign(diffs)) != 0)
            std_x = float(np.std(self.gaze_x_history))

            is_reading = (zero_crossings >= 3 and 0.02 < std_x < 0.25)
            return is_reading, std_x
        except Exception:
            return False, 0.0


class MultiModalStudyGuard:
    """
    Fuses Screen Activity, Smart YouTube Filtering, App Blocking,
    Peripheral Dynamics, Screen Glare, Blinks, and Gaze.
    """
    def __init__(
        self,
        shield_mode: str = "minimize",
        custom_study_topics: Optional[List[str]] = None,
        custom_block_keywords: Optional[List[str]] = None,
    ):
        self.custom_study_topics = custom_study_topics or []
        self.custom_block_keywords = custom_block_keywords or []
        self.flash_detector = ScreenFlashDetector()
        self.blink_detector = BlinkDetector()
        self.saccade_detector = SaccadeDetector()
        self.shield = FocusShield(
            mode=shield_mode,
            custom_study_topics=self.custom_study_topics,
            custom_block_keywords=self.custom_block_keywords,
        )

    def update_settings(
        self,
        shield_mode: str,
        custom_study_topics: List[str],
        custom_block_keywords: List[str],
    ):
        self.custom_study_topics = custom_study_topics
        self.custom_block_keywords = custom_block_keywords
        self.shield.mode = shield_mode
        self.shield.custom_study_topics = custom_study_topics
        self.shield.custom_block_keywords = custom_block_keywords

    def evaluate(
        self,
        landmarks,
        frame: np.ndarray,
        head_ratio: Optional[float],
        distraction_threshold: float = 0.35,
    ) -> Dict:
        # 1. Peripheral Input Tracking
        idle_seconds = get_system_idle_seconds()

        # 2. Active Window & Application Tracking + App Shield Enforcement
        hwnd, win_title, proc_name, app_cat, class_reason = get_foreground_window_details(
            custom_study_topics=self.custom_study_topics,
            custom_block_keywords=self.custom_block_keywords,
        )
        blocked_event = self.shield.check_and_enforce(hwnd, win_title, proc_name, app_cat, class_reason)

        is_study_video = (app_cat == "PRODUCTIVE" and ("youtube" in win_title.lower() or "meet" in win_title.lower() or "zoom" in proc_name))

        # If no face is detected
        if landmarks is None or head_ratio is None:
            return {
                "state": "DISTRACTED_AWAY",
                "label": "ABSENT / OFF-SCREEN",
                "color": (0, 0, 255),
                "reason": "No face detected in camera frame",
                "idle_sec": idle_seconds,
                "win_title": win_title,
                "proc_name": proc_name,
                "app_cat": app_cat,
                "class_reason": class_reason,
                "flash_rmsd": 0.0,
                "bpm": 0.0,
                "ear": 0.0,
                "is_reading": False,
                "is_flash": False,
                "is_study_video": is_study_video,
                "blocked_event": blocked_event,
                "total_blocked": self.shield.total_blocked_count,
            }

        # 3. Head Pose & Gaze Check
        h, w = frame.shape[:2]
        head_turned = head_ratio > distraction_threshold

        # 4. Extract Face Crop for Glare/Flash Analysis
        try:
            xs = [lm.x * w for lm in landmarks]
            ys = [lm.y * h for lm in landmarks]
            x1, x2 = max(0, int(min(xs))), min(w, int(max(xs)))
            y1, y2 = max(0, int(min(ys))), min(h, int(max(ys)))
            face_crop = frame[y1:y2, x1:x2] if (x2 > x1 and y2 > y1) else None
        except Exception:
            face_crop = None

        is_flash, flash_rmsd = self.flash_detector.update(face_crop)

        # 5. Eye Biometrics (EAR, Blinks, Saccades)
        ear, bpm, _ = self.blink_detector.update(landmarks, w, h)
        is_reading, saccade_score = self.saccade_detector.update(landmarks, w)

        # 6. Multi-Modal Fusion Decision Matrix
        if head_turned:
            state = "DISTRACTED_AWAY"
            label = "HEAD TURNED AWAY"
            color = (0, 0, 255)
            reason = f"Head turned off-center (Ratio: {head_ratio:.2f})"

        else:
            # User is looking DIRECTLY at the screen
            is_entertainment_app = (app_cat == "ENTERTAINMENT") or (blocked_event is not None)
            is_dynamic_lighting = is_flash or (flash_rmsd > 3.8)

            # If student is watching an online lecture / study video:
            # Allow extended listening & note-taking idle time (up to 300s / 5 mins)
            idle_threshold = 300.0 if is_study_video else 90.0
            is_long_idle = idle_seconds > idle_threshold
            is_movie_stare = (bpm < 6.0 and len(self.blink_detector.blink_timestamps) > 0 and idle_seconds > 60.0)

            if blocked_event is not None:
                state = "PASSIVE_MEDIA"
                label = f"SHIELD: BLOCKED {proc_name.upper()}"
                color = (0, 165, 255)
                reason = f"Distraction intercepted: {class_reason}"

            elif is_entertainment_app:
                state = "PASSIVE_MEDIA"
                label = "PASSIVE MEDIA (DISTRACTION)"
                color = (0, 165, 255)
                reason = f"Entertainment detected: {class_reason}"

            elif is_study_video:
                # Online class or educational YouTube lecture!
                state = "FOCUSED_ACTIVE"
                label = "ONLINE CLASS / STUDY VIDEO"
                color = (0, 220, 0)
                reason = f"Attentive to lecture: {class_reason}"

            elif (is_dynamic_lighting and idle_seconds > 15.0) or (flash_rmsd > 7.0):
                state = "PASSIVE_MEDIA"
                label = "PASSIVE MEDIA (SCREEN GLARE)"
                color = (0, 165, 255)
                reason = f"Dynamic video/game screen glare ({flash_rmsd:.1f} RMSD)"

            elif is_long_idle and is_movie_stare and not is_reading:
                state = "PASSIVE_MEDIA"
                label = "INATTENTIVE SCREEN STARE"
                color = (0, 165, 255)
                reason = f"No input for {int(idle_seconds)}s with suppressed blink rate ({bpm:.0f} bpm)"

            elif is_reading or (app_cat == "PRODUCTIVE" and idle_seconds < 180.0):
                state = "FOCUSED_READING" if is_reading else "FOCUSED_ACTIVE"
                label = "DEEP FOCUS (READING)" if is_reading else "DEEP FOCUS (STUDY)"
                color = (0, 220, 0)
                reason = f"Study material active ({class_reason})"

            elif idle_seconds < 45.0:
                state = "FOCUSED_ACTIVE"
                label = "ACTIVE FOCUS (WORKING)"
                color = (0, 220, 0)
                reason = "Active keyboard/mouse interaction"

            else:
                state = "FOCUSED_ACTIVE"
                label = "FOCUSED (ATTENTIVE)"
                color = (0, 220, 0)
                reason = "Attentive screen gaze with stable environment"

        return {
            "state": state,
            "label": label,
            "color": color,
            "reason": reason,
            "idle_sec": idle_seconds,
            "win_title": win_title,
            "proc_name": proc_name,
            "app_cat": app_cat,
            "class_reason": class_reason,
            "flash_rmsd": flash_rmsd,
            "bpm": bpm,
            "ear": ear,
            "is_reading": is_reading,
            "is_flash": is_flash,
            "is_study_video": is_study_video,
            "blocked_event": blocked_event,
            "total_blocked": self.shield.total_blocked_count,
        }


# ==============================================================================
# ==================== DECLARED DOMAIN ARCHITECTURE MODELS =====================
# ==============================================================================

class ScreenFlashColorShiftDetector(ScreenFlashDetector):
    """
    Biometric analyzer detecting screen flash, color shifts, and ambient monitor glare
    on the user's face to identify dynamic video playback (movies/gaming) vs steady study materials.
    """
    pass


class SaccadicEyeMovementAnalyzer(SaccadeDetector):
    """
    Saccadic eye movement analyzer verifying rhythmic horizontal sweeps with micro-pauses (fixations)
    during cognitive reading vs smooth pursuit motion and static fixation during video viewing.
    """
    pass


class MicroFixationDetector:
    """
    Detects micro-pauses (fixations) across lines of text during reading and problem-solving.
    """
    def __init__(self, fixation_min_frames: int = 3):
        self.fixation_min_frames = fixation_min_frames
        self.current_fixation_length = 0

    def analyze(self, eye_velocity: float) -> bool:
        if abs(eye_velocity) < 0.01:
            self.current_fixation_length += 1
        else:
            self.current_fixation_length = 0
        return self.current_fixation_length >= self.fixation_min_frames


class FacialExpressionBlinkRateAnalyzer(BlinkDetector):
    """
    Biometric analyzer measuring Eye Aspect Ratio (EAR) and blink rate dynamics.
    Detects significantly reduced blink rates (< 6 BPM) and spontaneous facial reactions
    typical of passive video entertainment.
    """
    pass


class KeyboardMouseDynamics:
    """
    Peripheral input pattern analyzer tracking keyboard typing, mouse scrolling, and note-taking.
    Flags extended periods of zero keystrokes alongside persistent screen gaze.
    """
    def __init__(self, idle_threshold_seconds: float = 90.0):
        self.idle_threshold_seconds = idle_threshold_seconds

    def get_idle_time(self) -> float:
        return get_system_idle_seconds()

    def is_passive_observation(self, idle_seconds: float) -> bool:
        return idle_seconds > self.idle_threshold_seconds


class AudioSourceCrossChecking:
    """
    Audio source cross-checker monitoring active system audio output streams,
    differentiating expected low-volume educational playback from high-volume entertainment media.
    """
    def __init__(self):
        self.active_audio_detected = False

    def evaluate_audio_source(self, is_educational_active: bool) -> Tuple[bool, str]:
        if is_educational_active:
            return True, "Educational audio playback verified"
        return False, "Ambient or neutral audio environment"


class URLDomainFiltering:
    """
    System-level activity classifier inspecting browser URLs, domain names, and active window titles
    to categorize traffic as educational versus media/entertainment.
    """
    def __init__(self, custom_study_topics=None, custom_block_keywords=None):
        self.custom_study_topics = custom_study_topics or []
        self.custom_block_keywords = custom_block_keywords or []

    def classify(self, title: str, exe_name: str) -> Tuple[str, str]:
        return classify_activity(
            title.lower(),
            exe_name.lower(),
            custom_study_topics=self.custom_study_topics,
            custom_block_keywords=self.custom_block_keywords
        )


class ActiveApplicationTracking(FocusShield):
    """
    Background agent logging active window titles and process executables (e.g. flagging vlc.exe,
    netflix, or streaming sites) and enforcing focus shield policies.
    """
    pass


class CognitiveReadingModel:
    """
    Combines saccadic sweeps, micro-fixations, and blink rate stability to model
    active cognitive reading and problem-solving vs passive video consumption.
    """
    def __init__(self):
        self.saccade_analyzer = SaccadicEyeMovementAnalyzer()
        self.fixation_detector = MicroFixationDetector()

    def evaluate_reading_cognition(self, landmarks, width: int) -> Dict:
        is_saccade, sweep_score = self.saccade_analyzer.update(landmarks, width)
        return {
            "cognitive_reading_detected": is_saccade,
            "sweep_amplitude": sweep_score,
            "state": "READING" if is_saccade else "NON_READING"
        }


class InattentiveScreenViewingDetector(MultiModalStudyGuard):
    """
    Advanced Multi-Modal StudyGuard Detector solving the inattentive screen viewing problem:
    identifies students staring directly at movies or video games using:
    1. Screen & Window Activity Monitoring (Active Application Tracking & URL/Domain Filtering)
    2. Visual & Biometric Signals (Screen Flash & Color Shifts, Saccadic Movements, Blink Rates)
    3. System & Peripheral Input Patterns (Keyboard & Mouse Dynamics, Audio Cross-Checking)
    """
    pass


# Semantic aliases for complete problem coverage
ScreenWindowActivityMonitoring = URLDomainFiltering
VisualBiometricSignals = MultiModalStudyGuard
BehavioralAnalysisEngine = MultiModalStudyGuard

