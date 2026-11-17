
import re


MAX_QUERY_LENGTH = 2000

JAILBREAK_PATTERNS = [
    r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+instructions\b",
    r"\bdisregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above)\s+instructions\b",
    r"\b(?:reveal|show|print|expose|repeat)\b.{0,50}\b(?:system prompt|hidden instructions|developer message)\b",
    r"\bact as (?:an? )?(?:unrestricted|uncensored|unfiltered) assistant\b",
    r"\b(?:DAN mode|developer mode)\b",
    r"\b(?:bypass|disable|override)\b.{0,40}\b(?:safety|guardrails|restrictions|instructions)\b",
]

CODE_GENERATION_PATTERNS = [
    r"\b(?:write|generate|create|build|implement|produce)\b.{0,50}\b(?:code|script|program|function|snippet)\b",
    r"\b(?:give me|show me|provide)\b.{0,30}\b(?:code|script|program|implementation)\b",
]

MALICIOUS_PATTERNS = [
    r"\b(?:create|build|deploy|write)\b.{0,40}\b(?:malware|ransomware|keylogger|credential stealer)\b",
    r"\b(?:steal|exfiltrate|harvest)\b.{0,40}\b(?:passwords|credentials|tokens|private keys)\b",
    r"\b(?:phish|spoof)\b.{0,40}\b(?:login|credentials|users)\b",
    r"\b(?:bypass|break into|gain unauthorized access to)\b.{0,40}\b(?:account|server|system|database)\b",
]

RECIPE_PATTERNS = [
    r"\b(?:recipe|recipes|ingredients|cooking instructions|meal plan)\b",
    r"\bhow to (?:cook|bake|prepare a meal)\b",
]


def validate_user_input(question: str) -> tuple[bool, str]:
    """
    Validate user input before sending it to the LLM.

    Returns:
        (True, "") if the input passes.
        (False, rejection_message) otherwise.
    """

    if not isinstance(question, str):
        return False, "Invalid question format."

    question = question.strip()

    if not question:
        return False, "Please enter a question."

    if len(question) > MAX_QUERY_LENGTH:
        return False, "Your question exceeds the maximum allowed length."

    if len(question) < 2:
        return False, "Please provide a meaningful question."

    normalized_question = question.lower()

    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, normalized_question):
            return False, (
                "Your request contains instructions that conflict "
                "with the assistant's security policies."
            )

    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, normalized_question):
            return False, (
                "I cannot assist with malicious or unauthorized activities."
            )

    for pattern in CODE_GENERATION_PATTERNS:
        if re.search(pattern, normalized_question):
            return False, (
                "Code generation is outside the scope of this "
                "Enterprise RAG Assistant."
            )

    for pattern in RECIPE_PATTERNS:
        if re.search(pattern, normalized_question):
            return False, (
                "Recipe and cooking requests are outside the scope "
                "of this Enterprise RAG Assistant."
            )

    return True, ""


def validate_input_format(question: str) -> tuple[bool, str]:
    """
    Perform basic deterministic input validation only.
    """

    if not isinstance(question, str):
        return False, "Invalid question format."

    question = question.strip()

    if not question:
        return False, "Please enter a question."

    if len(question) > MAX_QUERY_LENGTH:
        return False, "Your question exceeds the maximum allowed length."

    if len(question) < 2:
        return False, "Please provide a meaningful question."

    return True, ""
