import re


OFF_TOPIC_PATTERNS = [
    r"\blegal\b|\blaw\b|\bcompliance advice\b|\bdiscrimination\b",
    r"\bsalary\b|\bcompensation\b|\bpay band\b",
    r"\binterview questions\b|\binterview strategy\b",
    r"\bwrite (a )?job description\b|\bjob ad\b",
    r"\bresume\b|\bcv\b",
]

INJECTION_PATTERNS = [
    r"ignore (all )?((previous|above) )?(system )?instructions",
    r"reveal (your )?(prompt|system)",
    r"act as .*instead",
    r"jailbreak",
    r"developer message",
]


def is_prompt_injection(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in INJECTION_PATTERNS)


def is_off_topic(text: str) -> bool:
    lower = text.lower()
    if any(re.search(pattern, lower) for pattern in OFF_TOPIC_PATTERNS):
        return True
    shl_terms = ["assessment", "test", "shl", "opq", "gsa", "hiring", "candidate", "role"]
    hiring_context = any(term in lower for term in shl_terms)
    unrelated = any(term in lower for term in ["weather", "recipe", "movie", "travel", "homework"])
    return unrelated and not hiring_context
