import re


WHATSAPP_RE = re.compile(r"\b(?:https?://)?(?:www\.)?(?:wa\.me/\d+|whatsapp\.com/send\?phone=\d+)\b", re.IGNORECASE)
TELEGRAM_RE = re.compile(r"\b(?:https?://)?(?:www\.)?t\.me/[a-zA-Z0-9_]+\b", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"\b(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+(?:/\S*)?\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
URL_RE = re.compile(r"\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{7,}\d)(?!\w)")


def sanitize_chatter_message(text: str | None) -> str:
    if not text:
        return ""
    sanitized = str(text)
    sanitized = WHATSAPP_RE.sub("[phone hidden]", sanitized)
    sanitized = TELEGRAM_RE.sub("[contact hidden]", sanitized)
    sanitized = LINKEDIN_RE.sub("[contact hidden]", sanitized)
    sanitized = EMAIL_RE.sub("[email hidden]", sanitized)
    sanitized = URL_RE.sub("[link hidden]", sanitized)
    sanitized = PHONE_RE.sub("[phone hidden]", sanitized)
    return sanitized


def has_contact_details(text: str | None) -> bool:
    if not text:
        return False
    return any(pattern.search(str(text)) for pattern in (WHATSAPP_RE, TELEGRAM_RE, LINKEDIN_RE, EMAIL_RE, URL_RE, PHONE_RE))
