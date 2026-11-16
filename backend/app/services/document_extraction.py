from pathlib import Path

import pymupdf
from docx import Document as DocxDocument


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCUMENT_STORAGE_DIR = (
    PROJECT_ROOT / "data" / "documents"
)


def get_safe_file_path(storage_path: str) -> Path:
    """
    Resolve a stored document path and ensure
    it remains inside the document storage directory.
    """

    file_path = (PROJECT_ROOT / storage_path).resolve()
    storage_root = DOCUMENT_STORAGE_DIR.resolve()

    try:
        file_path.relative_to(storage_root)
    except ValueError:
        raise ValueError("Invalid document storage path")

    if not file_path.is_file():
        raise FileNotFoundError("Document file not found")

    return file_path


def extract_pdf(file_path: Path) -> str:

    extracted_pages = []

    with pymupdf.open(file_path) as pdf:

        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")

        for page in pdf:
            page_text = page.get_text("text")

            if page_text.strip():
                extracted_pages.append(page_text)

    return "\n\n".join(extracted_pages)


def extract_docx(file_path: Path) -> str:

    document = DocxDocument(file_path)

    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n\n".join(paragraphs)


def extract_txt(file_path: Path) -> str:

    return file_path.read_text(encoding="utf-8")


def clean_text(text: str) -> str:
    """
    Basic text normalization while preserving paragraphs.
    """

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = []

    for line in text.split("\n"):
        cleaned_line = " ".join(line.split())
        lines.append(cleaned_line)

    text = "\n".join(lines)

    # Limit excessive blank lines.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def extract_document_text(
    storage_path: str,
    file_type: str
) -> str:

    file_path = get_safe_file_path(storage_path)

    file_type = file_type.upper()

    if file_type == "PDF":
        extracted_text = extract_pdf(file_path)

    elif file_type == "DOCX":
        extracted_text = extract_docx(file_path)

    elif file_type == "TXT":
        extracted_text = extract_txt(file_path)

    else:
        raise ValueError("Unsupported document type")

    cleaned_text = clean_text(extracted_text)

    if not cleaned_text:
        raise ValueError(
            "No readable text found in the document. "
            "Scanned PDFs may require OCR."
        )

    return cleaned_text