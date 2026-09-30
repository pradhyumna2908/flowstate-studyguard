import os
import sys
from typing import List
import numpy as np
import pytest

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import study_guard



class MockLandmarkPoint:
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z


@pytest.fixture
def mock_landmarks() -> List[MockLandmarkPoint]:
    """
    Fixture 1: Generates a full synthetic set of 478 MediaPipe face landmarks
    with calibrated anatomical eye and iris positions for attentive gaze.
    """
    landmarks = [MockLandmarkPoint(0.5, 0.5) for _ in range(478)]
    # Nose tip
    landmarks[1] = MockLandmarkPoint(0.50, 0.50)
    # Left eye landmarks (corners & eyelids)
    landmarks[33] = MockLandmarkPoint(0.38, 0.45)   # Outer corner
    landmarks[133] = MockLandmarkPoint(0.46, 0.45)  # Inner corner
    landmarks[160] = MockLandmarkPoint(0.42, 0.43)  # Top 1
    landmarks[158] = MockLandmarkPoint(0.44, 0.43)  # Top 2
    landmarks[144] = MockLandmarkPoint(0.42, 0.47)  # Bottom 1
    landmarks[153] = MockLandmarkPoint(0.44, 0.47)  # Bottom 2
    # Right eye landmarks (corners & eyelids)
    landmarks[362] = MockLandmarkPoint(0.54, 0.45)  # Inner corner
    landmarks[263] = MockLandmarkPoint(0.62, 0.45)  # Outer corner
    landmarks[385] = MockLandmarkPoint(0.56, 0.43)  # Top 1
    landmarks[387] = MockLandmarkPoint(0.58, 0.43)  # Top 2
    landmarks[373] = MockLandmarkPoint(0.56, 0.47)  # Bottom 1
    landmarks[380] = MockLandmarkPoint(0.58, 0.47)  # Bottom 2
    # Irises
    landmarks[468] = MockLandmarkPoint(0.42, 0.45)  # Left iris
    landmarks[473] = MockLandmarkPoint(0.58, 0.45)  # Right iris
    return landmarks


@pytest.fixture
def synthetic_frame_tensor() -> np.ndarray:
    """
    Fixture 2: Generates a 3-channel BGR video frame with valid dimensions (480, 640, 3).
    """
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    return frame


@pytest.fixture
def flash_detector() -> study_guard.ScreenFlashColorShiftDetector:
    """
    Fixture 3: Instantiates screen flash and color shift biometric detector.
    """
    return study_guard.ScreenFlashColorShiftDetector(history_size=24, flash_threshold=3.5)


@pytest.fixture
def study_guard_detector() -> study_guard.InattentiveScreenViewingDetector:
    """
    Fixture 4: Instantiates multi-modal StudyGuard detection engine with active shield.
    """
    return study_guard.InattentiveScreenViewingDetector(shield_mode="minimize")


@pytest.fixture
def focus_shield() -> study_guard.FocusShield:
    """
    Fixture 5: Instantiates active FocusShield app blocker.
    """
    return study_guard.FocusShield(mode="minimize")
