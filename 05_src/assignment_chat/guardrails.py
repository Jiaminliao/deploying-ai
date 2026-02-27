import re

BANNED = [
    r"\bcat(s)?\b",
    r"\bdog(s)?\b",
    r"\bhoroscope(s)?\b",
    r"\bzodiac\b",
    r"taylor\s+swift",
]

PROMPT_LEAK = [
    r"system prompt",
    r"developer message",
    r"reveal.*prompt",
    r"show.*prompt",
    r"ignore.*instructions",
]

def check_guardrails(user_text: str):
    text = user_text.lower()

    for pat in PROMPT_LEAK:
        if re.search(pat, text):
            return False, "Sorry — I can’t share or modify system/developer instructions."

    for pat in BANNED:
        if re.search(pat, text):
            return False, "Sorry — I am not allowed to chat with that topic. Please ask something else."

    return True, ""