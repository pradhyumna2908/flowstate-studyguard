"""
Tests for FocusShield, ActiveApplicationTracking, and Smart YouTube Domain Filtering.
"""

import pytest
import study_guard


@pytest.mark.parametrize(
    "title,exe,expected_category,should_block",
    [
        # Educational Classes & Lectures (Allowed)
        ("Calculus 1 - Full College Course - YouTube - Google Chrome", "chrome.exe", "PRODUCTIVE", False),
        ("Class 12 Physics Chapter 1 One Shot Revision - YouTube", "msedge.exe", "PRODUCTIVE", False),
        ("Python Tutorial for Beginners [Full Course] - YouTube", "chrome.exe", "PRODUCTIVE", False),
        ("CS50 2024 - Lecture 1 - C - YouTube", "chrome.exe", "PRODUCTIVE", False),
        ("MIT OpenCourseWare 18.06 Linear Algebra - YouTube", "chrome.exe", "PRODUCTIVE", False),
        ("Khan Academy - Derivatives Introduction - YouTube", "brave.exe", "PRODUCTIVE", False),
        # Entertainment Videos & Distractions on YouTube (Blocked)
        ("Taylor Swift - Cruel Summer (Official Music Video) - YouTube", "chrome.exe", "ENTERTAINMENT", True),
        ("MrBeast $500,000 In A Plane Challenge - YouTube", "chrome.exe", "ENTERTAINMENT", True),
        ("GTA 6 Official Gameplay Trailer 4K - YouTube", "chrome.exe", "ENTERTAINMENT", True),
        ("Funny Cats Memes Compilation - YouTube", "chrome.exe", "ENTERTAINMENT", True),
        ("YouTube - Google Chrome", "chrome.exe", "ENTERTAINMENT", True),
        ("Shorts - YouTube", "chrome.exe", "ENTERTAINMENT", True),
    ],
)
def test_smart_youtube_filtering(focus_shield, title, exe, expected_category, should_block):
    """Asserts that educational lectures are allowed while entertainment/shorts are blocked."""
    cat, reason = study_guard.classify_activity(title.lower(), exe.lower())
    assert cat == expected_category
    is_blocked = focus_shield.is_distraction(title.lower(), exe.lower(), cat)
    assert is_blocked is should_block


def test_whitelist_protection(focus_shield):
    """Asserts that essential productivity and study tools are never blocked."""
    protected_cases = [
        ("Visual Studio Code - app.py", "code.exe"),
        ("Microsoft Word - Thesis.docx", "winword.exe"),
        ("Notion - Study Notes", "notion.exe"),
        ("Obsidian - Computer Science Vault", "obsidian.exe"),
        ("Adobe Acrobat Reader - Textbook.pdf", "acrobat.exe"),
        ("Zoom Meeting - Mathematics Lecture", "zoom.exe"),
        ("FlowState - Multi-Modal StudyGuard", "chrome.exe"),
    ]
    for title, exe in protected_cases:
        cat, reason = study_guard.classify_activity(title.lower(), exe.lower())
        assert focus_shield.is_protected(title.lower(), exe.lower()) is True
        assert focus_shield.is_distraction(title.lower(), exe.lower(), cat) is False


def test_custom_study_and_block_lists():
    """Asserts custom keyword overrides for domain and application filtering."""
    custom_topics = ["biochemistry", "pathology", "fluid mechanics"]
    custom_blocks = ["solitaire", "chess.com", "instagram"]

    # Custom study topic allowed on YouTube
    cat1, _ = study_guard.classify_activity(
        "Biochemistry Pathway Lecture - YouTube", "chrome.exe", custom_study_topics=custom_topics
    )
    assert cat1 == "PRODUCTIVE"

    # Custom block term blocked
    cat2, _ = study_guard.classify_activity(
        "Instagram - Reels", "chrome.exe", custom_block_keywords=custom_blocks
    )
    assert cat2 == "ENTERTAINMENT"


def test_url_domain_filter_class():
    """Tests URLDomainFiltering formal domain model class."""
    filter_obj = study_guard.URLDomainFiltering(
        custom_study_topics=["dsa", "leetcode"],
        custom_block_keywords=["tiktok"]
    )
    cat, reason = filter_obj.classify("LeetCode Problem 1 - Two Sum", "chrome.exe")
    assert cat == "PRODUCTIVE"
