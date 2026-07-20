"""
parse.py — Stage 1: document I/O with validation. Zero LLM calls.

Validate-before-LLM rule (study material §5): catch empty/image-based/
oversized inputs here, before a single token is spent.
"""

import re
import sys

from pypdf import PdfReader

MIN_RESUME_CHARS = 200     # below this the PDF is likely image-based
MIN_JD_CHARS = 100
MAX_CHARS = 24_000         # ≈ 6,000 tokens at 4 chars/token


def read_resume_pdf(path: str) -> str:
    """Extract clean plain text from a PDF résumé.

    Raises ValueError if the file is missing/unreadable or the extracted
    text is shorter than 200 characters (image-based PDF).
    """
    try:
        reader = PdfReader(path)
    except FileNotFoundError:
        raise ValueError(f"Résumé file not found: {path}")
    except Exception as exc:
        raise ValueError(f"Could not open résumé PDF '{path}': {exc}")

    if len(reader.pages) > 2:
        print(
            f"WARNING: résumé is {len(reader.pages)} pages — "
            "1 page is the recommended maximum.",
            file=sys.stderr,
        )

    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < MIN_RESUME_CHARS:
        raise ValueError(
            f"Extracted only {len(text)} characters from '{path}'. "
            "The PDF is likely image-based (scanned) — export a native PDF "
            "from a word processor instead."
        )

    if len(text) > MAX_CHARS:
        print(
            f"WARNING: résumé text truncated to {MAX_CHARS} chars.",
            file=sys.stderr,
        )
        text = text[:MAX_CHARS]

    return text


def read_jd_text(path: str) -> str:
    """Read a plain-text job description file.

    Raises ValueError if the file is missing or shorter than 100
    characters after stripping whitespace.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        raise ValueError(f"Job description file not found: {path}")

    text = text.strip()
    if len(text) < MIN_JD_CHARS:
        raise ValueError(
            f"Job description '{path}' has only {len(text)} characters — "
            "it looks empty or truncated."
        )

    return text
