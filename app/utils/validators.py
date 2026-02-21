import re


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_username(username: str) -> bool:
    return bool(username) and 3 <= len(username) <= 80


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))
