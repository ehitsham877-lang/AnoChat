import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.messages.sanitize import sanitize_chatter_message


def test_sanitize_email():
    assert sanitize_chatter_message("Please email me at john@gmail.com") == "Please email me at [email hidden]"


def test_sanitize_phone():
    assert sanitize_chatter_message("Call me at +1 555 123 4567") == "Call me at [phone hidden]"


def test_sanitize_url():
    assert sanitize_chatter_message("Visit https://example.com") == "Visit [link hidden]"


def test_sanitize_whatsapp():
    assert sanitize_chatter_message("Message me on wa.me/15551234567") == "Message me on [phone hidden]"


def test_sanitize_telegram():
    assert sanitize_chatter_message("Telegram: t.me/myusername") == "Telegram: [contact hidden]"


def test_normal_message_unchanged():
    assert sanitize_chatter_message("Normal project update message") == "Normal project update message"
