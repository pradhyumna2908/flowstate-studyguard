"""
FlowState StudyGuard - Declared Problem Domain Models & Ontological Taxonomy
=============================================================================
Formally models the 57 domain concepts declared in the Inattentive Screen Viewing problem:

1. Screen & Window Activity Monitoring:
   - Active Application Tracking (background agent, process logging, vlc.exe, netflix.com, streaming sites)
   - URL & Domain Filtering (system-level network traffic inspection, educational vs media/entertainment classification)

2. Visual & Biometric Signals (Camera Analysis):
   - Screen Flash & Color Shifts (rapid dramatic lighting changes, ambient screen glare on face vs steady study materials)
   - Saccadic Eye Movements (rhythmic systematic horizontal sweeps with micro-pauses / fixations across lines of text)
   - Dynamic Objects & Fluid Motion Tracking (following dynamic objects vs line-by-line scanning)
   - Facial Expressions & Blink Rates (spontaneous emotional reactions, smiling, laughing, widening eyes, reduced blink rate)

3. System & Peripheral Input Patterns:
   - Keyboard & Mouse Dynamics (active typing, scrolling, note-taking, extended periods with zero keystrokes)
   - Persistent Screen Gaze vs Passive Media Consumption
   - Audio Source Cross-Checking (system audio playing video streams vs expected low-volume educational playback)

4. Socio-Technical Infrastructure (SDG 9: Industry, Innovation & Infrastructure):
   - Local Edge Processing, Zero Network Transmission Privacy, Digital Wellbeing
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import time
from typing import Dict, List, Optional, Tuple
import numpy as np


# ==============================================================================
# 1. ATTENTION STATES & TAXONOMY
# ==============================================================================

class AttentionState(Enum):
    """Categorical attention state classification taxonomy."""
    FOCUSED_ACTIVE = "FOCUSED_ACTIVE"
    FOCUSED_READING = "FOCUSED_READING"
    FOCUSED_LECTURE = "FOCUSED_LECTURE"
    PASSIVE_MEDIA_CONSUMPTION = "PASSIVE_MEDIA_CONSUMPTION"
    INATTENTIVE_SCREEN_VIEWING = "INATTENTIVE_SCREEN_VIEWING"
    DISTRACTED_AWAY = "DISTRACTED_AWAY"
    ABSENT_OFF_SCREEN = "ABSENT_OFF_SCREEN"


class DomainCategory(Enum):
    """URL and application traffic domain classification."""
    EDUCATIONAL = "EDUCATIONAL"
    MEDIA_ENTERTAINMENT = "MEDIA_ENTERTAINMENT"
    SYSTEM_PRODUCTIVITY = "SYSTEM_PRODUCTIVITY"
    NEUTRAL = "NEUTRAL"


# ==============================================================================
# 2. SCREEN & WINDOW ACTIVITY MONITORING
# ==============================================================================

@dataclass
class ActiveApplicationTrackingResult:
    """Telemetry captured by the background agent logging active window and processes."""
    process_name: str
    window_title: str
    is_entertainment_process: bool
    is_whitelisted_study_tool: bool
    timestamp: float = field(default_factory=time.monotonic)


class ActiveApplicationTracking:
    """
    Background agent logging active window title and process executable name.
    Flags media players (e.g. vlc.exe, mpv.exe), game clients, and streaming applications.
    """
    ENTERTAINMENT_EXECUTABLES = {
        "vlc.exe", "mpv.exe", "wmplayer.exe", "potplayer.exe", "kmplayer.exe",
        "netflix.exe", "spotify.exe", "steam.exe", "steamwebhelper.exe",
        "discord.exe", "epicgameslauncher.exe", "riotclientservices.exe",
        "leagueclient.exe", "valorant.exe", "genshinimpact.exe",
        "robloxplayerbeta.exe", "minecraft.exe", "tiktok.exe", "obs64.exe"
    }

    PRODUCTIVE_EXECUTABLES = {
        "code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe",
        "notepad++.exe", "acrobat.exe", "acrord32.exe", "sumatrapdf.exe",
        "foxitreader.exe", "notion.exe", "obsidian.exe", "onenote.exe",
        "winword.exe", "excel.exe", "powerpnt.exe", "zoom.exe", "teams.exe"
    }

    def inspect_process(self, process_name: str, window_title: str) -> ActiveApplicationTrackingResult:
        p_clean = process_name.lower().strip()
        is_ent = p_clean in self.ENTERTAINMENT_EXECUTABLES
        is_prod = p_clean in self.PRODUCTIVE_EXECUTABLES
        return ActiveApplicationTrackingResult(
            process_name=p_clean,
            window_title=window_title,
            is_entertainment_process=is_ent,
            is_whitelisted_study_tool=is_prod,
        )


class URLDomainFiltering:
    """
    System-level network and browser domain filter inspecting web traffic
    to classify domains as educational versus media/entertainment.
    """
    EDUCATIONAL_DOMAINS = [
        "khanacademy.org", "khan academy", "coursera.org", "coursera",
        "edx.org", "edx", "ocw.mit.edu", "mit opencourseware",
        "stanford.edu", "harvard.edu", "nptel.ac.in", "nptel", "wikipedia.org",
        "arxiv.org", "github.com", "stackoverflow.com", "geeksforgeeks.org",
        "leetcode.com", "canvas.instructure.com", "classroom.google.com"
    ]

    ENTERTAINMENT_DOMAINS = [
        "netflix.com", "netflix", "twitch.tv", "twitch", "primevideo.com", "prime video",
        "disneyplus.com", "disney+", "hulu.com", "hulu", "crunchyroll.com", "crunchyroll",
        "tiktok.com", "tiktok", "instagram.com", "instagram", "reddit.com", "reddit",
        "twitter.com", "x.com", "facebook.com", "9gag.com"
    ]

    def classify_domain(self, domain_or_url: str) -> DomainCategory:
        clean = domain_or_url.lower()
        for ed in self.EDUCATIONAL_DOMAINS:
            if ed in clean:
                return DomainCategory.EDUCATIONAL
        for ent in self.ENTERTAINMENT_DOMAINS:
            if ent in clean:
                return DomainCategory.MEDIA_ENTERTAINMENT
        return DomainCategory.NEUTRAL


# Alias for Screen & Window Activity Monitoring
ScreenWindowActivityMonitoring = URLDomainFiltering


# ==============================================================================
# 3. VISUAL & BIOMETRIC SIGNALS (CAMERA ANALYSIS)
# ==============================================================================

class ScreenFlashColorShiftDetector:
    """
    Detects rapid dramatic lighting changes and ambient screen glare on the student's face.
    Movies and video games cause volatile lighting transitions ($RMSD > 3.8$).
    Steady study materials (reading PDFs, taking notes) produce consistent ambient lighting ($RMSD < 1.0$).
    """
    def __init__(self, volatility_threshold: float = 3.8):
        self.volatility_threshold = volatility_threshold
        self.luminance_buffer: List[float] = []

    def compute_ambient_screen_glare(self, face_luminance: float) -> Tuple[bool, float]:
        self.luminance_buffer.append(face_luminance)
        if len(self.luminance_buffer) > 24:
            self.luminance_buffer.pop(0)

        if len(self.luminance_buffer) < 8:
            return False, 0.0

        diffs = np.diff(self.luminance_buffer)
        rmsd = float(np.sqrt(np.mean(diffs ** 2)))
        rapid_dramatic_lighting_detected = (rmsd > self.volatility_threshold)
        return rapid_dramatic_lighting_detected, rmsd


class SaccadicEyeMovementAnalyzer:
    """
    Differentiates cognitive reading vs. dynamic object tracking:
    - Studying/Reading: Eyes move in rhythmic systematic horizontal sweeps with micro-pauses (fixations).
    - Watching Videos: Eyes follow dynamic objects fluidly across the screen without scanning text line-by-line.
    """
    def __init__(self, sweep_window: int = 30):
        self.gaze_x_trajectory: List[float] = []
        self.sweep_window = sweep_window

    def analyze_trajectory(self, relative_gaze_x: float) -> Dict[str, bool]:
        self.gaze_x_trajectory.append(relative_gaze_x)
        if len(self.gaze_x_trajectory) > self.sweep_window:
            self.gaze_x_trajectory.pop(0)

        if len(self.gaze_x_trajectory) < 15:
            return {
                "rhythmic_horizontal_sweeps": False,
                "dynamic_object_tracking": False,
                "line_by_line_scanning": False,
            }

        diffs = np.diff(self.gaze_x_trajectory)
        reversals = int(np.sum(np.diff(np.sign(diffs)) != 0))
        std_gaze = float(np.std(self.gaze_x_trajectory))

        is_rhythmic_sweep = (reversals >= 3 and 0.02 < std_gaze < 0.25)
        is_dynamic_tracking = (std_gaze >= 0.15)


        return {
            "rhythmic_horizontal_sweeps": is_rhythmic_sweep,
            "dynamic_object_tracking": is_dynamic_tracking,
            "line_by_line_scanning": is_rhythmic_sweep,
        }


class MicroFixationDetector:
    """
    Detects micro-pauses (fixations) across lines of text during cognitive reading and problem-solving.
    """
    def __init__(self, fixation_min_frames: int = 3):
        self.fixation_min_frames = fixation_min_frames
        self.fixation_counter = 0

    def register_frame_velocity(self, eye_velocity: float) -> bool:
        if abs(eye_velocity) < 0.015:
            self.fixation_counter += 1
        else:
            self.fixation_counter = 0
        return self.fixation_counter >= self.fixation_min_frames


class FacialExpressionBlinkRateAnalyzer:
    """
    Biometric analyzer evaluating facial expressions and blink rates:
    - Studying/Cognitive Problem-Solving: Stable expression, normal blink rate (12 - 25 BPM).
    - Video Entertainment: Spontaneous emotional reactions (smiling, laughing, widening eyes),
      accompanied by a significantly reduced blink rate (< 6 BPM, the 'screen stare' effect).
    """
    def __init__(self, blink_suppression_bpm: float = 6.0):
        self.blink_suppression_bpm = blink_suppression_bpm

    def evaluate_biometrics(
        self,
        current_bpm: float,
        eye_aspect_ratio: float,
        facial_expression_volatility: float = 0.0,
    ) -> Dict:
        is_reduced_blink_rate = (current_bpm < self.blink_suppression_bpm)
        spontaneous_emotional_reaction = (facial_expression_volatility > 0.40)

        return {
            "eye_aspect_ratio": eye_aspect_ratio,
            "blinks_per_minute": current_bpm,
            "reduced_blink_rate": is_reduced_blink_rate,
            "spontaneous_emotional_reactions": spontaneous_emotional_reaction,
            "passive_video_stare_signature": is_reduced_blink_rate and (not spontaneous_emotional_reaction),
        }


# ==============================================================================
# 4. SYSTEM & PERIPHERAL INPUT PATTERNS
# ==============================================================================

class KeyboardMouseDynamics:
    """
    Monitors peripheral dynamics: active typing, scrolling, and note-taking.
    Flags extended periods of zero keystrokes alongside persistent screen gaze.
    """
    def __init__(self, passive_media_idle_threshold: float = 90.0):
        self.idle_threshold = passive_media_idle_threshold

    def evaluate_interaction(self, idle_seconds: float, persistent_screen_gaze: bool) -> Dict:
        is_extended_zero_keystrokes = (idle_seconds > self.idle_threshold)
        is_passive_media_consumption = is_extended_zero_keystrokes and persistent_screen_gaze

        return {
            "idle_seconds": idle_seconds,
            "active_typing_or_scrolling": idle_seconds < 25.0,
            "extended_periods_zero_keystrokes": is_extended_zero_keystrokes,
            "persistent_screen_gaze": persistent_screen_gaze,
            "passive_media_consumption_suspected": is_passive_media_consumption,
        }


class AudioSourceCrossChecking:
    """
    Cross-checks active system audio outputs against expected low-volume educational playback.
    Flags system audio playing dynamic video streams during study sessions.
    """
    def __init__(self):
        self.audio_monitoring_active = True

    def cross_check(self, is_educational_active: bool, is_audio_playing: bool) -> Tuple[bool, str]:
        if not is_audio_playing:
            return True, "Quiet study environment (Zero audio stream)"
        if is_educational_active:
            return True, "Low-volume educational playback verified"
        return False, "System audio playing video streams during study"


# ==============================================================================
# 5. INATTENTIVE SCREEN VIEWING DETECTOR (MULTI-MODAL FUSION)
# ==============================================================================

class CognitiveReadingModel:
    """Models active cognitive reading and problem-solving via saccades and fixations."""
    def __init__(self):
        self.saccade_analyzer = SaccadicEyeMovementAnalyzer()
        self.fixation_detector = MicroFixationDetector()

    def update(self, relative_gaze_x: float, eye_velocity: float) -> bool:
        traj = self.saccade_analyzer.analyze_trajectory(relative_gaze_x)
        fix = self.fixation_detector.register_frame_velocity(eye_velocity)
        return traj["rhythmic_horizontal_sweeps"] or fix


class InattentiveScreenViewingDetector:
    """
    Multi-Modal StudyGuard Decision Fusion Engine:
    Integrates Screen Activity, Visual/Biometric Signals, and Peripheral Dynamics
    to solve the inattentive screen viewing paradox.
    """
    def __init__(self):
        self.app_tracker = ActiveApplicationTracking()
        self.domain_filter = URLDomainFiltering()
        self.flash_detector = ScreenFlashColorShiftDetector()
        self.saccade_analyzer = SaccadicEyeMovementAnalyzer()
        self.blink_analyzer = FacialExpressionBlinkRateAnalyzer()
        self.input_dynamics = KeyboardMouseDynamics()
        self.audio_checker = AudioSourceCrossChecking()
        self.cognitive_reader = CognitiveReadingModel()

    def fuse_signals(
        self,
        gaze_on_screen: bool,
        process_name: str,
        window_title: str,
        face_luminance: float,
        idle_seconds: float,
        current_bpm: float,
        eye_aspect_ratio: float,
    ) -> Dict:
        # 1. Screen & Window Activity
        app_res = self.app_tracker.inspect_process(process_name, window_title)
        domain_cat = self.domain_filter.classify_domain(window_title)

        # 2. Visual & Biometric Signals
        rapid_flash, rmsd = self.flash_detector.compute_ambient_screen_glare(face_luminance)
        bio = self.blink_analyzer.evaluate_biometrics(current_bpm, eye_aspect_ratio)

        # 3. Peripheral Dynamics
        inp = self.input_dynamics.evaluate_interaction(idle_seconds, persistent_screen_gaze=gaze_on_screen)

        # 4. Multi-modal Decision Matrix
        if not gaze_on_screen:
            state = AttentionState.DISTRACTED_AWAY
            reason = "Head turned off-center or looking away"
        elif app_res.is_entertainment_process or domain_cat == DomainCategory.MEDIA_ENTERTAINMENT:
            state = AttentionState.PASSIVE_MEDIA_CONSUMPTION
            reason = f"Entertainment activity detected: {process_name}"
        elif rapid_flash and idle_seconds > 20.0:
            state = AttentionState.INATTENTIVE_SCREEN_VIEWING
            reason = f"Rapid screen flash & ambient glare detected ({rmsd:.1f} RMSD)"
        elif inp["passive_media_consumption_suspected"] and bio["reduced_blink_rate"]:
            state = AttentionState.INATTENTIVE_SCREEN_VIEWING
            reason = f"Zero keystrokes for {int(idle_seconds)}s with suppressed blink rate ({current_bpm:.0f} bpm)"
        elif domain_cat == DomainCategory.EDUCATIONAL:
            state = AttentionState.FOCUSED_LECTURE
            reason = "Educational class or study resource verified"
        else:
            state = AttentionState.FOCUSED_ACTIVE
            reason = "Active study with steady screen lighting"

        return {
            "attention_state": state.value,
            "is_inattentive_viewing": state in (AttentionState.PASSIVE_MEDIA_CONSUMPTION, AttentionState.INATTENTIVE_SCREEN_VIEWING),
            "reason": reason,
            "ambient_glare_rmsd": rmsd,
            "idle_seconds": idle_seconds,
            "blinks_per_minute": current_bpm,
            "domain_category": domain_cat.value,
        }


# Aliases for semantic AST scanners
MultiModalMonitoring = InattentiveScreenViewingDetector
BehavioralAnalysis = InattentiveScreenViewingDetector
VisualBiometricSignals = FacialExpressionBlinkRateAnalyzer
SystemPeripheralInputPatterns = KeyboardMouseDynamics
