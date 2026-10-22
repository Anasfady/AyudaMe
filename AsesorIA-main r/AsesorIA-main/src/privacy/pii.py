"""PII redaction before embedding/LLM calls.

First-pass regex detection for common Spanish identifiers.

Known limitation:
    Regex detection can produce false positives.

Names and organisations require NER and are intentionally left as a
future improvement.
"""

from __future__ import annotations

import re


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "IBAN",
        re.compile(
            r"\bES\d{2}(?:[ ]?\d{4}){5}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "EMAIL",
        re.compile(
            r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NIF",
        re.compile(
            r"\b\d{8}[A-Za-z]\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NIE",
        re.compile(
            r"\b[XYZxyz]\d{7}[A-Za-z]\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CIF",
        re.compile(
            r"\b[ABCDEFGHJNPQRSUVWabcdefghjnpqrsuvw]"
            r"\d{7}[0-9A-Ja-j]\b",
        ),
    ),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+34[\s.-]?)?"
            r"[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}"
            r"(?!\d)"
        ),
    ),
]


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Replace detected identifiers with [LABEL] placeholders.

    Args:
        text:
            User-provided text to sanitize.

    Returns:
        A tuple containing:
        - the sanitized text;
        - one label for each replacement performed.

    Example:
        >>> redact_pii("Contacta con 612345678")
        (
            "Contacta con [PHONE]",
            ["PHONE"],
        )
    """
    found: list[str] = []

    for label, pattern in _PATTERNS:
        text, count = pattern.subn(f"[{label}]", text)
        found.extend([label] * count)

    return text, found