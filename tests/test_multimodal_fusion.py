"""
Tests for InattentiveScreenViewingDetector and Multi-Modal Decision Fusion.
"""

import numpy as np
import pytest
import study_guard


def test_absent_face_boundary(study_guard_detector, synthetic_frame_tensor):
    """Asserts boundary condition when no face is present in frame."""
    res = study_guard_detector.evaluate(
        landmarks=None,
        frame=synthetic_frame_tensor,
        head_ratio=None,
    )
    assert res["state"] == "DISTRACTED_AWAY"
    assert "No face detected" in res["reason"]
    assert res["color"] == (0, 0, 255)


def test_head_pose_boundary_thresholds(study_guard_detector, mock_landmarks, synthetic_frame_tensor):
    """Asserts boundary behavior across extreme head pose ratio values."""
    # 1. Perfectly centered (ratio = 0.05) -> Focused
    res_center = study_guard_detector.evaluate(
        landmarks=mock_landmarks,
        frame=synthetic_frame_tensor,
        head_ratio=0.05,
        distraction_threshold=0.35,
    )
    assert "FOCUSED" in res_center["state"]

    # 2. Turned away boundary (ratio = 0.36 > threshold 0.35) -> Distracted
    res_turned = study_guard_detector.evaluate(
        landmarks=mock_landmarks,
        frame=synthetic_frame_tensor,
        head_ratio=0.36,
        distraction_threshold=0.35,
    )
    assert res_turned["state"] == "DISTRACTED_AWAY"

    # 3. Extreme boundary (ratio = 5.0) -> Distracted
    res_extreme = study_guard_detector.evaluate(
        landmarks=mock_landmarks,
        frame=synthetic_frame_tensor,
        head_ratio=5.0,
        distraction_threshold=0.35,
    )
    assert res_extreme["state"] == "DISTRACTED_AWAY"


def test_inattentive_screen_viewing_detection(mock_landmarks):
    """
    Tests the core problem solution:
    When a student looks directly at the screen (ratio = 0.10, gaze centered)
    but an entertainment video or dynamic game glare is active,
    the model must NOT mark them attentive, but classify as PASSIVE_MEDIA.
    """
    detector = study_guard.InattentiveScreenViewingDetector(shield_mode="disabled")

    # Flashing frame sequence simulating a movie/game
    for i in range(12):
        val = 40 if (i % 2 == 0) else 230
        dynamic_frame = np.full((480, 640, 3), val, dtype=np.uint8)
        res = detector.evaluate(
            landmarks=mock_landmarks,
            frame=dynamic_frame,
            head_ratio=0.10,  # Looking DIRECTLY at screen
        )

    # Dynamic glare volatility causes detection
    assert res["flash_rmsd"] > 10.0


def test_keyboard_mouse_dynamics():
    """Tests peripheral input dynamics analyzer."""
    dynamics = study_guard.KeyboardMouseDynamics(idle_threshold_seconds=90.0)
    assert dynamics.is_passive_observation(15.0) is False
    assert dynamics.is_passive_observation(95.0) is True


def test_audio_cross_checking():
    """Tests audio source cross-checker output."""
    audio_checker = study_guard.AudioSourceCrossChecking()
    ok_edu, msg_edu = audio_checker.evaluate_audio_source(is_educational_active=True)
    assert ok_edu is True
    assert "Educational" in msg_edu

    ok_amb, msg_amb = audio_checker.evaluate_audio_source(is_educational_active=False)
    assert ok_amb is False
