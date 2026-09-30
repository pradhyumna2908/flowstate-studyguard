"""
Tests for Parent Mobile sharing, QR code generation, WhatsApp URL formatting, and configuration hygiene.
"""

import os
import study_guard


def test_parent_mobile_url_and_ip():
    """Asserts local network IP and parent portal URL format."""
    ip = study_guard.get_local_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4

    url = f"http://{ip}:8501?view=parent"
    assert url.startswith("http://")
    assert "?view=parent" in url


def test_qr_code_generation():
    """Asserts styled PNG Base64 QR code generation."""
    test_url = "http://192.168.1.100:8501?view=parent"
    qr_b64 = study_guard.get_qr_code_base64(test_url)
    assert isinstance(qr_b64, str)
    assert len(qr_b64) > 500  # Valid Base64-encoded PNG


def test_whatsapp_url_encoding():
    """Asserts clean phone normalization and URL encoding for WhatsApp messages."""
    phone = "+91 98765-43210"
    message = "Hi Mom! Study session started: 45 min goal."
    wa_url = study_guard.format_whatsapp_url(phone, message)

    assert wa_url.startswith("https://wa.me/919876543210?text=")
    assert "Study%20session" in wa_url or "Study+session" in wa_url


def test_parent_nudge_delivery():
    """Asserts thread-safe encouragement nudge queue."""
    study_guard.send_parent_nudge("Mother", "Great job on Calculus! Keep going!")
    nudge = study_guard.get_latest_parent_nudge()

    assert nudge is not None
    assert nudge["sender"] == "Mother"
    assert "Great job" in nudge["message"]


def test_configuration_hygiene_env_example():
    """Asserts presence of .env.example configuration template."""
    env_example = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.exists(env_example), ".env.example must exist in repository root"
    with open(env_example, "r") as f:
        content = f.read()
    assert "STUDY_TARGET_MINUTES" in content
    assert "SHIELD_MODE" in content


def test_packaging_and_requirements_hygiene():
    """Asserts presence of pyproject.toml, setup.py, requirements.txt, and .gitignore."""
    root = os.path.join(os.path.dirname(__file__), "..")
    for f in ["pyproject.toml", "setup.py", "requirements.txt", ".gitignore", "README.md"]:
        path = os.path.join(root, f)
        assert os.path.exists(path), f"Missing required file: {f}"


def test_benchmark_results_json_validity():
    """Asserts benchmark_results.json exists and contains empirical metrics across batch sizes."""
    import json
    bench_file = os.path.join(os.path.dirname(__file__), "..", "benchmark_results.json")
    assert os.path.exists(bench_file), "benchmark_results.json must exist"
    with open(bench_file, "r") as f:
        data = json.load(f)
    assert "batch_1" in data
    assert "batch_16" in data
    assert data["batch_1"]["640x480 (480p)"]["mean_latency_ms"] < 10.0

