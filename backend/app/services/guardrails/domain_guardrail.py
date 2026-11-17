
import re


ALLOWED_DOMAIN_KEYWORDS = {
    "HR": [
        "hr",
        "human resources",
        "employee",
        "employees",
        "annual leave",
        "leave",
        "vacation",
        "holiday",
        "attendance",
        "payroll",
        "salary",
        "manager",
        "onboarding",
        "benefit",
        "recruitment",
    ],

    "FINANCE": [
        "finance",
        "reimbursement",
        "expense",
        "expenses",
        "invoice",
        "receipt",
        "claim",
        "payment",
        "budget",
        "travel allowance",
        "business expense",
    ],

    "ENGINEERING_IT": [
        "engineering",
        "it support",
        "laptop",
        "equipment",
        "software access",
        "development tool",
        "repository",
        "repositories",
        "company device",
        "asset id",
        "damaged device",
        "technical support",
    ],
}

GENERAL_COMPANY_KEYWORDS = [
    "company policy",
    "internal policy",
    "company document",
    "company procedure",
]


def check_domain(question: str) -> tuple[bool, str]:
    """
    Check whether a question relates to supported enterprise domains.

    Returns:
        (True, matched_domain) if supported.
        (False, rejection_message) otherwise.
    """

    if not isinstance(question, str):
        return False, "Invalid question."

    normalized_question = question.lower()

    matched_domains = []

    for domain, keywords in ALLOWED_DOMAIN_KEYWORDS.items():

        for keyword in keywords:

            pattern = (
                r"(?<!\w)"
                + re.escape(keyword)
                + r"(?!\w)"
            )

            if re.search(pattern, normalized_question):
                matched_domains.append(domain)
                break

    if matched_domains:
        return True, ", ".join(matched_domains)

    for keyword in GENERAL_COMPANY_KEYWORDS:

        if keyword in normalized_question:
            return True, "GENERAL_COMPANY"

    return False, (
        "I can only answer questions related to company HR, "
        "Finance, and Engineering/IT policies and documents."
    )
