
import re


CITATION_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    re.IGNORECASE
)

ABSTENTION_PHRASES = [
    "i could not find sufficient information",
    "i could not find relevant information",
    "i could not find relevant, safe information",
    "there is insufficient information",
    "the documents do not contain sufficient information",
    "not available in the supplied documents",
]


def extract_citations(answer: str) -> list[int]:
    """
    Extract source numbers from citations such as
    [Source 1] and [Source 2].
    """

    matches = CITATION_PATTERN.findall(answer)

    return [int(number) for number in matches]


def is_abstention_response(answer: str) -> bool:
    """
    Identify responses that explicitly state that
    sufficient information is unavailable.
    """

    normalized = answer.strip().lower()

    return any(
        normalized.startswith(phrase)
        for phrase in ABSTENTION_PHRASES
    )


def validate_citations(
    answer: str,
    valid_source_numbers: set[int]
) -> tuple[bool, str]:
    """
    Verify that generated citations refer to sources
    actually supplied to the LLM.

    An explicit insufficient-information response
    does not require a citation.
    """

    if not isinstance(answer, str) or not answer.strip():
        return False, "The generated answer is empty."

    citations = extract_citations(answer)

    if not citations:
        if is_abstention_response(answer):
            return True, ""

        return False, "The answer does not contain source citations."

    invalid_citations = [
        number
        for number in citations
        if number not in valid_source_numbers
    ]

    if invalid_citations:
        return (
            False,
            f"Invalid source references detected: {invalid_citations}"
        )

    return True, ""
