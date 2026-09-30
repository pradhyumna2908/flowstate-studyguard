"""
Tests for Accessibility (WCAG 2.1 AA), Universal Design, Documentation Integrity, and Open Source Licensing.
"""

import os


def test_documentation_and_licensing_files_exist():
    """Asserts that all essential open source and accessibility files exist."""
    root = os.path.join(os.path.dirname(__file__), "..")
    required_files = [
        "LICENSE",
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "docs/ACCESSIBILITY.md",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "packages.txt",
        ".env.example",
    ]
    for rel_path in required_files:
        full_path = os.path.join(root, rel_path)
        assert os.path.exists(full_path), f"Required documentation/accessibility file missing: {rel_path}"


def test_license_contains_mit_terms():
    """Asserts MIT License text integrity."""
    license_path = os.path.join(os.path.dirname(__file__), "..", "LICENSE")
    with open(license_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "MIT License" in content
    assert "Permission is hereby granted" in content


def test_accessibility_doc_contains_wcag_and_aria_specs():
    """Asserts that ACCESSIBILITY.md covers WCAG 2.1 AA standards and keyboard navigation."""
    acc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "ACCESSIBILITY.md")
    with open(acc_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "WCAG 2.1" in content
    assert "Contrast Ratio" in content
    assert "Keyboard Navigation" in content
    assert "Screen Reader" in content


def test_readme_contains_sdg9_and_mathematical_formulation():
    """Asserts that README.md documents UN SDG 9 (Target 9.4) and mathematical equations."""
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SDG 9" in content
    assert "Target 9.4" in content
    assert "Bayesian" in content or "Inattentive" in content
