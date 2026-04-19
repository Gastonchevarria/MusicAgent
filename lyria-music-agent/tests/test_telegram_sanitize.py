import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sanitize_html_strips_tags():
    from pipeline.telegram_notifier import sanitize_html
    raw = 'The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.'
    result = sanitize_html(raw)
    assert "<" not in result
    assert ">" not in result
    assert "quota" in result


def test_sanitize_html_handles_none():
    from pipeline.telegram_notifier import sanitize_html
    assert sanitize_html(None) == "N/A"
    assert sanitize_html("") == "N/A"


def test_sanitize_html_preserves_clean_text():
    from pipeline.telegram_notifier import sanitize_html
    assert sanitize_html("simple error message") == "simple error message"


def test_clean_uses_sanitize():
    """_clean should strip HTML AND escape Telegram markdown."""
    from pipeline.telegram_notifier import _clean
    raw = '<HttpError 403 "quota_exceeded">'
    result = _clean(raw)
    assert "<" not in result
    assert ">" not in result


if __name__ == "__main__":
    test_sanitize_html_strips_tags()
    test_sanitize_html_handles_none()
    test_sanitize_html_preserves_clean_text()
    test_clean_uses_sanitize()
    print("ALL TELEGRAM SANITIZE TESTS PASSED")
