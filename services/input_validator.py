import re


def contains_sensitive_data(text: str) -> bool:
    patterns = [
        r"\b\d{10}\b",  # phone numbers
        r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}",  # emails
        r"\b\d{12}\b",  # Aadhaar
        r"[A-Z]{5}\d{4}[A-Z]{1}",  # PAN format
        r"\b\d{16}\b",  # card numbers
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def contains_prompt_injection(text: str) -> bool:
    injection_patterns = [
        "ignore previous instructions",
        "bypass security",
        "act as system",
        "you are no longer eva",
        "system:",
        "assistant:",
        "tell backend logs",
        "delete database",
        "run sql",
        "execute command",
        "use system role",
    ]

    text_low = text.lower()
    return any(pattern in text_low for pattern in injection_patterns)
