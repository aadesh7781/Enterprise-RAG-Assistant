
import re

from app.services.guardrails.citation_validator import (
    validate_citations
)


MAX_OUTPUT_LENGTH = 12000


CODE_OUTPUT_PATTERNS = [
    r"(?m)^\s*```",
    r"(?m)^\s*def\s+\w+\s*\(",
    r"(?m)^\s*class\s+\w+\s*[:\(]",
    r"(?m)^\s*import\s+\w+",
    r"(?m)^\s*from\s+\w+\s+import\s+",
    r"(?m)^\s*function\s+\w+\s*\(",
    r"(?m)^\s*<\?php",
]


def contains_code_output(answer: str) -> bool:
    """
    Detect obvious programming code in generated responses.

    This is a basic output restriction, not a complete
    programming-language detector.
    """

    for pattern in CODE_OUTPUT_PATTERNS:

        if re.search(pattern, answer):
            return True

    return False


def validate_llm_output(
    answer: str,
    valid_source_numbers: set[int]
) -> tuple[bool, str]:
    """
    Validate generated LLM responses before returning them
    to the application.
    """

    if not isinstance(answer, str):
        return False, "Invalid response format."

    answer = answer.strip()

    if not answer:
        return False, "The model generated an empty response."

    if len(answer) > MAX_OUTPUT_LENGTH:
        return False, "The generated response exceeds the allowed length."

    if contains_code_output(answer):
        return False, (
            "Generated programming code is outside the scope "
            "of this Enterprise RAG Assistant."
        )

    citations_valid, citation_message = validate_citations(
        answer,
        valid_source_numbers
    )

    if not citations_valid:
        return False, citation_message

    return True, ""
