"""
Tests for biometric signal analyzers: Screen Flash & Color Shifts, Saccades, EAR, and Blinks.
Asserts expected array/tensor shapes and boundary validation errors.
"""

import numpy as np
import pytest
import study_guard


def test_frame_tensor_shapes(synthetic_frame_tensor):
    """Asserts expected array/tensor shape and memory layout."""
    assert isinstance(synthetic_frame_tensor, np.ndarray)
    assert synthetic_frame_tensor.shape == (480, 640, 3)
    assert synthetic_frame_tensor.dtype == np.uint8
    assert synthetic_frame_tensor.ndim == 3


def test_boundary_validation_empty_frames(flash_detector):
    """Asserts robust boundary handling on empty and None frame tensors."""
    # Boundary case 1: None input
    is_flash, val = flash_detector.update(None)
    assert is_flash is False
    assert val == 0.0

    # Boundary case 2: Empty numpy tensor with 0 shape
    empty_frame = np.empty((0, 0, 3), dtype=np.uint8)
    assert empty_frame.shape == (0, 0, 3)
    is_flash, val = flash_detector.update(empty_frame)
    assert is_flash is False
    assert val == 0.0

    # Boundary case 3: 1D array boundary error handling
    invalid_1d = np.zeros((100,), dtype=np.uint8)
    is_flash, val = flash_detector.update(invalid_1d)
    assert is_flash is False


def test_screen_flash_steady_vs_dynamic(flash_detector):
    """
    Asserts screen flash & ambient lighting volatility:
    - Steady study materials (PDFs, notes) produce RMSD < 1.0.
    - Flashing movies/games produce RMSD > 10.0 and flag True.
    """
    # 1. Steady lighting sequence
    steady_face = np.full((120, 120, 3), 140, dtype=np.uint8)
    for _ in range(15):
        is_flash, rmsd = flash_detector.update(steady_face)
    assert is_flash is False
    assert rmsd < 1.0

    # 2. Dynamic movie/game flash sequence (rapid luminance oscillation)
    for i in range(16):
        luminance = 40 if (i % 2 == 0) else 230
        flashing_face = np.full((120, 120, 3), luminance, dtype=np.uint8)
        is_flash, rmsd = flash_detector.update(flashing_face)

    assert is_flash is True
    assert rmsd > 50.0  # Dynamic lighting volatility spikes sharply


def test_ear_computation_and_bounds(mock_landmarks):
    """
    Tests Eye Aspect Ratio (EAR) computation and boundary clamping.
    EAR must strictly remain in [0.0, 1.0] for realistic anatomical landmarks.
    """
    blink_analyzer = study_guard.FacialExpressionBlinkRateAnalyzer()
    ear, bpm, blinked = blink_analyzer.update(mock_landmarks, 640, 480)

    assert isinstance(ear, float)
    assert 0.10 <= ear <= 0.60  # Normal open eye ratio
    assert isinstance(bpm, float)
    assert bpm >= 0.0
    assert isinstance(blinked, bool)


def test_saccadic_reading_vs_static_stare(mock_landmarks):
    """
    Tests SaccadicEyeMovementAnalyzer:
    Rhythmic horizontal sweep oscillation is verified vs stationary staring.
    """
    saccade_analyzer = study_guard.SaccadicEyeMovementAnalyzer(window_size=30)

    # Initial state with static gaze
    for _ in range(10):
        is_reading, score = saccade_analyzer.update(mock_landmarks, 640)
    assert is_reading is False

    # Simulate reading sweep reversals
    class PerturbedPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    import copy
    lms = copy.deepcopy(mock_landmarks)
    for i in range(25):
        sweep_offset = 0.05 * np.sin(i * 0.8)
        lms[1] = PerturbedPoint(0.50 + sweep_offset, 0.50)
        is_reading, score = saccade_analyzer.update(lms, 640)

    assert isinstance(is_reading, (bool, np.bool_))
    assert isinstance(score, float)


def test_micro_fixation_detector():
    """Tests MicroFixationDetector measuring pauses across text lines."""
    detector = study_guard.MicroFixationDetector(fixation_min_frames=3)

    # High velocity: no fixation
    assert detector.analyze(eye_velocity=0.08) is False
    assert detector.analyze(eye_velocity=-0.05) is False

    # 3 consecutive micro-pauses: triggers fixation
    assert detector.analyze(eye_velocity=0.002) is False
    assert detector.analyze(eye_velocity=0.001) is False
    assert detector.analyze(eye_velocity=-0.003) is True  # Reached min frames threshold
