
import re


INJECTION_PATTERNS = [
    r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions\b",
    r"\bdisregard\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions\b",
    r"\breveal\b.{0,50}\b(?:system prompt|hidden instructions|secrets)\b",
    r"\b(?:override|bypass|disable)\b.{0,40}\b(?:system instructions|safety rules|guardrails)\b",
    r"\byou are now\b.{0,50}\b(?:unrestricted|unfiltered|administrator)\b",
    r"\bexfiltrate\b.{0,50}\b(?:data|credentials|secrets)\b",
]


def contains_prompt_injection(text: str) -> bool:
    """
    Detect common instruction-like prompt injection patterns.

    This is a basic heuristic detector, not a complete
    prompt injection security solution.
    """

    if not isinstance(text, str):
        return False

    normalized_text = text.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized_text):
            return True

    return False


def filter_suspicious_chunks(chunks: list[dict]) -> list[dict]:
    """
    Exclude chunks containing detected injection patterns.

    The original retrieved chunks are not modified.
    """

    safe_chunks = []

    for chunk in chunks:
        content = chunk.get("text", "")

        if contains_prompt_injection(content):
            continue

        safe_chunks.append(chunk)

    return safe_chunks
