from pathlib import Path

from app.services.document_processor import process_document


DOCUMENT_DIR = Path("data/documents")

for file_path in DOCUMENT_DIR.iterdir():

    if not file_path.is_file():
        continue

    file_type = file_path.suffix.lstrip(".").upper()

    if file_type not in {"PDF", "DOCX", "TXT"}:
        continue

    storage_path = f"data/documents/{file_path.name}"

    print("\n" + "=" * 60)
    print(f"DOCUMENT: {file_path.name}")

    try:
        chunks = process_document(
            storage_path=storage_path,
            file_type=file_type,
            chunk_size=800,
            chunk_overlap=150
        )

        print("PROCESSING SUCCESSFUL")
        print("Total chunks:", len(chunks))
        print("Total characters:", sum(len(c) for c in chunks))

        for index, chunk in enumerate(chunks[:3]):
            print(f"\nCHUNK {index + 1}")
            print(chunk[:300])

    except Exception as error:
        print("PROCESSING FAILED:", error)