from pathlib import Path

from app.services.document_extraction import extract_document_text


DOCUMENT_DIR = Path("data/documents")

for file_path in DOCUMENT_DIR.iterdir():

    if not file_path.is_file():
        continue

    file_type = file_path.suffix.lstrip(".").upper()

    if file_type not in {"PDF", "DOCX", "TXT"}:
        continue

    storage_path = f"data/documents/{file_path.name}"

    print("\n" + "=" * 60)
    print("FILE:", file_path.name)

    try:
        text = extract_document_text(storage_path, file_type)

        print("EXTRACTION SUCCESSFUL")
        print("CHARACTERS:", len(text))
        print("PREVIEW:")
        print(text[:500])

    except Exception as error:
        print("EXTRACTION FAILED:", error)