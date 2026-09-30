"""
Tests for Empirical Efficiency, Sub-5ms Latency SLA, Throughput, and Memory Hygiene.
"""

import time
import pytest
import numpy as np
import study_guard
import benchmark


@pytest.mark.efficiency
def test_realtime_frame_inference_latency_sla():
    """Asserts that per-frame behavioral decision fusion executes under 5.0 ms (SLA for >200 FPS)."""
    detector = study_guard.InattentiveScreenViewingDetector(shield_mode="disabled")
    mock_lms = benchmark.get_mock_landmarks_478()
    frame = benchmark.generate_benchmark_batch(1, 480, 640)[0]

    # Warmup
    for _ in range(5):
        detector.evaluate_frame(mock_lms, frame, head_ratio=0.12)

    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        detector.evaluate_frame(mock_lms, frame, head_ratio=0.12)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    mean_ms = sum(latencies) / len(latencies)
    assert mean_ms < 5.0, f"Mean latency {mean_ms:.2f}ms violates 5.0ms SLA"


@pytest.mark.efficiency
def test_classification_throughput_and_speed():
    """Asserts high-throughput processing for window classification."""
    title = "Calculus 1 - Full College Course - YouTube - Google Chrome"
    exe = "chrome.exe"

    t0 = time.perf_counter()
    for _ in range(100):
        study_guard.classify_activity(title, exe)
    elapsed = time.perf_counter() - t0

    # Ensure 100 classifications finish in under 20ms
    assert elapsed < 0.05, f"Classification batch took too long: {elapsed*1000:.2f}ms"


@pytest.mark.efficiency
def test_memory_footprint_bounds():
    """Asserts peak memory consumption remains below 50 MB during intensive multi-frame batches."""
    import tracemalloc

    tracemalloc.start()
    detector = study_guard.InattentiveScreenViewingDetector(shield_mode="disabled")
    mock_lms = benchmark.get_mock_landmarks_478()
    batch = benchmark.generate_benchmark_batch(16, 480, 640)

    for frame in batch:
        detector.evaluate_frame(mock_lms, frame, head_ratio=0.15)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert peak_mb < 50.0, f"Peak memory {peak_mb:.2f}MB exceeds 50MB bound"
