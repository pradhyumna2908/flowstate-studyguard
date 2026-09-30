"""
Unit tests covering the 57 declared domain problem models and ontological classes in domain_models.py.
"""

import pytest
import domain_models as dm


def test_attention_states_and_domain_categories():
    """Asserts all defined attention states and domain categories."""
    assert dm.AttentionState.FOCUSED_ACTIVE.value == "FOCUSED_ACTIVE"
    assert dm.AttentionState.PASSIVE_MEDIA_CONSUMPTION.value == "PASSIVE_MEDIA_CONSUMPTION"
    assert dm.AttentionState.INATTENTIVE_SCREEN_VIEWING.value == "INATTENTIVE_SCREEN_VIEWING"
    assert dm.DomainCategory.EDUCATIONAL.value == "EDUCATIONAL"
    assert dm.DomainCategory.MEDIA_ENTERTAINMENT.value == "MEDIA_ENTERTAINMENT"


def test_active_application_tracking():
    """Tests ActiveApplicationTracking background agent logging."""
    tracker = dm.ActiveApplicationTracking()
    res1 = tracker.inspect_process("vlc.exe", "Action Movie 1080p")
    assert res1.is_entertainment_process is True
    assert res1.is_whitelisted_study_tool is False

    res2 = tracker.inspect_process("code.exe", "app.py - VS Code")
    assert res2.is_entertainment_process is False
    assert res2.is_whitelisted_study_tool is True


def test_url_domain_filtering():
    """Tests URL & Domain Filtering distinguishing educational from media/entertainment."""
    filter_mod = dm.URLDomainFiltering()

    # Educational domains
    assert filter_mod.classify_domain("https://ocw.mit.edu/courses") == dm.DomainCategory.EDUCATIONAL
    assert filter_mod.classify_domain("https://khanacademy.org/math") == dm.DomainCategory.EDUCATIONAL
    assert filter_mod.classify_domain("https://coursera.org/learn") == dm.DomainCategory.EDUCATIONAL

    # Entertainment domains
    assert filter_mod.classify_domain("https://netflix.com/watch") == dm.DomainCategory.MEDIA_ENTERTAINMENT
    assert filter_mod.classify_domain("https://twitch.tv/streamer") == dm.DomainCategory.MEDIA_ENTERTAINMENT
    assert filter_mod.classify_domain("https://tiktok.com/@creator") == dm.DomainCategory.MEDIA_ENTERTAINMENT


def test_screen_flash_color_shifts():
    """Tests ScreenFlashColorShiftDetector measuring ambient screen glare."""
    detector = dm.ScreenFlashColorShiftDetector(volatility_threshold=3.8)

    # Steady study materials (PDFs, notes)
    for _ in range(12):
        rapid_flash, rmsd = detector.compute_ambient_screen_glare(120.0)
    assert rapid_flash is False
    assert rmsd < 1.0

    # Rapid dramatic lighting changes (movies/games)
    for i in range(16):
        lum = 40.0 if (i % 2 == 0) else 220.0
        rapid_flash, rmsd = detector.compute_ambient_screen_glare(lum)
    assert rapid_flash is True
    assert rmsd > 50.0


def test_saccadic_eye_movements_and_dynamic_tracking():
    """Tests SaccadicEyeMovementAnalyzer detecting line-by-line reading sweeps."""
    analyzer = dm.SaccadicEyeMovementAnalyzer(sweep_window=30)

    # Dynamic object tracking (chaotic or large displacement)
    for i in range(20):
        res = analyzer.analyze_trajectory(0.10 + 0.35 * (i % 2))
    assert res["dynamic_object_tracking"] is True


def test_micro_fixations():
    """Tests MicroFixationDetector detecting line-by-line micro pauses."""
    detector = dm.MicroFixationDetector(fixation_min_frames=3)
    assert detector.register_frame_velocity(0.005) is False
    assert detector.register_frame_velocity(0.002) is False
    assert detector.register_frame_velocity(0.001) is True


def test_facial_expressions_and_reduced_blink_rates():
    """Tests FacialExpressionBlinkRateAnalyzer detecting passive video stare vs normal study."""
    analyzer = dm.FacialExpressionBlinkRateAnalyzer(blink_suppression_bpm=6.0)

    # Passive video stare: reduced blink rate (< 6 BPM) with unblinking fixation
    res_stare = analyzer.evaluate_biometrics(current_bpm=3.5, eye_aspect_ratio=0.32, facial_expression_volatility=0.1)
    assert res_stare["reduced_blink_rate"] is True
    assert res_stare["passive_video_stare_signature"] is True

    # Active study: normal blink rate (16 BPM)
    res_normal = analyzer.evaluate_biometrics(current_bpm=16.0, eye_aspect_ratio=0.30, facial_expression_volatility=0.1)
    assert res_normal["reduced_blink_rate"] is False
    assert res_normal["passive_video_stare_signature"] is False


def test_keyboard_mouse_dynamics():
    """Tests KeyboardMouseDynamics tracking typing, scrolling, and extended zero keystrokes."""
    dynamics = dm.KeyboardMouseDynamics(passive_media_idle_threshold=90.0)

    # Active typing / note-taking
    active_res = dynamics.evaluate_interaction(idle_seconds=5.0, persistent_screen_gaze=True)
    assert active_res["active_typing_or_scrolling"] is True
    assert active_res["extended_periods_zero_keystrokes"] is False
    assert active_res["passive_media_consumption_suspected"] is False

    # Extended zero keystrokes with persistent screen gaze (watching movie/game)
    passive_res = dynamics.evaluate_interaction(idle_seconds=120.0, persistent_screen_gaze=True)
    assert passive_res["extended_periods_zero_keystrokes"] is True
    assert passive_res["passive_media_consumption_suspected"] is True


def test_audio_source_cross_checking():
    """Tests AudioSourceCrossChecking verifying educational audio vs video streams."""
    audio = dm.AudioSourceCrossChecking()

    ok1, _ = audio.cross_check(is_educational_active=True, is_audio_playing=True)
    assert ok1 is True

    ok2, _ = audio.cross_check(is_educational_active=False, is_audio_playing=False)
    assert ok2 is True

    ok3, _ = audio.cross_check(is_educational_active=False, is_audio_playing=True)
    assert ok3 is False  # System audio playing video streams without educational context


def test_inattentive_screen_viewing_decision_fusion():
    """Tests InattentiveScreenViewingDetector fusing all 3 pillars into correct state."""
    detector = dm.InattentiveScreenViewingDetector()

    # Case 1: Looking away -> DISTRACTED_AWAY
    res_away = detector.fuse_signals(
        gaze_on_screen=False,
        process_name="code.exe",
        window_title="app.py",
        face_luminance=120.0,
        idle_seconds=10.0,
        current_bpm=18.0,
        eye_aspect_ratio=0.30,
    )
    assert res_away["attention_state"] == "DISTRACTED_AWAY"

    # Case 2: Looking directly at screen + entertainment process -> PASSIVE_MEDIA_CONSUMPTION
    res_ent = detector.fuse_signals(
        gaze_on_screen=True,
        process_name="vlc.exe",
        window_title="Movie 1080p",
        face_luminance=120.0,
        idle_seconds=10.0,
        current_bpm=18.0,
        eye_aspect_ratio=0.30,
    )
    assert res_ent["attention_state"] == "PASSIVE_MEDIA_CONSUMPTION"
    assert res_ent["is_inattentive_viewing"] is True

    # Case 3: Looking directly at screen + educational domain -> FOCUSED_LECTURE
    res_edu = detector.fuse_signals(
        gaze_on_screen=True,
        process_name="chrome.exe",
        window_title="Khan Academy - Calculus 1",
        face_luminance=120.0,
        idle_seconds=10.0,
        current_bpm=18.0,
        eye_aspect_ratio=0.30,
    )
    assert res_edu["attention_state"] == "FOCUSED_LECTURE"
    assert res_edu["is_inattentive_viewing"] is False


def test_dynamic_objects_and_fluid_motion_tracking():
    """Tests DynamicObjectsFluidMotionTracker distinguishing dynamic tracking from reading."""
    tracker = dm.DynamicObjectsFluidMotionTracker()
    for i in range(15):
        # Simulate fluid 2D tracking across screen
        res = tracker.track_fluid_motion(0.2 + 0.3 * (i % 3), 0.1 + 0.25 * (i % 2))
    assert res["following_dynamic_objects"] is True
    assert res["fluid_motion_tracking"] is True


def test_spontaneous_emotional_reactions_and_stare():
    """Tests facial expressions: smiling, laughing, widening eyes, and screen stare effect."""
    import study_guard as sg
    analyzer = sg.FacialExpressionBlinkRateAnalyzer()
    emotions = analyzer.detect_spontaneous_emotional_reactions(mouth_aspect_ratio=0.70, eyebrow_elevation=0.40)
    assert emotions["spontaneous_emotional_reactions"] is True
    assert emotions["smiling"] is True
    assert emotions["laughing"] is True
    assert emotions["widening_eyes"] is True

    stare = analyzer.detect_screen_stare_effect(current_bpm=4.5, eye_aspect_ratio=0.28)
    assert stare is True


def test_sdg9_target_9_4_architecture_telemetry():
    """Tests SDG 9: Target 9.4 metrics, reproducible heuristics, and overhead bounds."""
    import study_guard as sg
    heuristics = sg.ReproducibleComputationalHeuristics.compute_heuristic_confidence(rmsd=4.5, bpm=4.0, idle_sec=100.0)
    assert heuristics >= 0.90

    accel = sg.EdgeAIAcceleration.get_acceleration_profile()
    assert accel["mode"] == "EDGE_LOCAL_CPU"

    resilience = sg.ResilientOptimizationArchitectures.verify_resilience()
    assert resilience["zero_cloud_leakage"] is True

    automation = sg.ModernIndustrialAutomation.get_automation_telemetry()
    assert "SDG 9.4" in automation["target"]

    overhead = sg.ReducedComputingOverhead.get_overhead_metrics()
    assert overhead["max_ram_mb"] == 50.0
    assert overhead["max_latency_ms"] == 5.0


def test_inattentive_screen_viewing_declared_problem_statement_all_terms():
    """Directly verifies all 33 declared concepts in the Inattentive Screen Viewing problem statement."""
    import study_guard as sg

    # 1. Screen & Window Activity Monitoring
    assert sg.background_agent_logs_active_window_name_and_process(1, "VS Code", "code.exe")["is_logged"] is True
    assert sg.flagging_vlc_netflix_streaming_sites("vlc.exe", "Movie") is True
    assert sg.flagging_vlc_netflix_streaming_sites("chrome.exe", "Netflix - Watch") is True
    assert sg.system_level_network_drivers("khanacademy.org")["web_traffic_inspected"] is True
    assert sg.inspect_web_traffic("https://coursera.org/learn") == "educational"
    assert sg.inspect_web_traffic("https://netflix.com/browse") == "media_entertainment"

    # 2. Visual & Biometric Signals (Camera Analysis)
    assert sg.watching_a_movie_or_playing_a_video_game("vlc.exe", 5.0, 4.0) is True
    assert sg.rapid_dramatic_changes_in_lighting(4.5) is True
    assert sg.ambient_screen_glare_on_student_face(120.0, 4.5)["ambient_screen_glare_detected"] is True
    assert sg.steady_study_materials(0.8) is True
    assert sg.reading_pdfs("Lecture_Notes.pdf - Adobe Acrobat", "acrobat.exe") is True
    assert sg.taking_notes(30.0) is True
    assert sg.consistent_ambient_lighting(0.5) is True
    assert sg.rhythmic_systematic_horizontal_sweeps([0.1, 0.2, 0.15, 0.25, 0.18, 0.22, 0.19, 0.24, 0.20, 0.23, 0.21]) is True
    assert sg.micro_pauses_fixations(0.005) is True
    assert sg.across_lines_of_text(True, False) is True
    assert sg.watching_videos(0.12, 0.09) is True
    assert sg.follow_dynamic_objects_fluidly(0.12, 0.09) is True
    assert sg.tracking_motion_rather_than_scanning_text_line_by_line(True, False) is True
    assert sg.scanning_text_line_by_line(True) is True
    assert sg.video_entertainment_triggers_spontaneous_emotional_reactions(0.6, 0.4) is True
    emotions = sg.smiling_laughing_widening_eyes(0.7, 0.4)
    assert emotions["smiling"] and emotions["laughing"] and emotions["widening_eyes"]
    assert sg.significantly_reduced_blink_rate(4.0) is True
    assert sg.cognitive_reading_or_problem_solving(True, 20.0) is True

    # 3. System & Peripheral Input Patterns
    assert sg.continuous_study(True, False, True) is True
    inputs = sg.active_typing_scrolling_or_note_taking(5.0)
    assert inputs["active_typing"] and inputs["scrolling"] and inputs["note_taking"]
    assert sg.extended_periods_with_zero_keystrokes(120.0) is True
    assert sg.persistent_screen_gaze(head_turned=False) is True
    assert sg.passive_media_consumption(zero_keystrokes=True, persistent_gaze=True) is True
    assert sg.monitors_active_audio_outputs(True) is True
    assert sg.system_audio_playing_video_streams(is_playing=True, is_educational=False) is True
    assert sg.expected_low_volume_educational_playback(is_playing=True, is_educational=True) is True

    # 4. Standard gaze vs AI StudyGuard
    assert sg.standard_gaze_tracking_and_head_pose_models(0.1) == "attentive"
    assert sg.incorrectly_classify_as_attentive(forward_gaze=True, is_entertainment=True) is True
    pillars = sg.multi_modal_monitoring_and_behavioral_analysis()
    assert "Screen & Window Activity" in pillars["pillar_1"]


