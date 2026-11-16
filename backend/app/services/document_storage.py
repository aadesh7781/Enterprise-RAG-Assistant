from pathlib import Path, PurePosixPath
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

from fastapi import UploadFile


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCUMENT_STORAGE_DIR = PROJECT_ROOT / "data" / "documents"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_file(file_path: Path, extension: str) -> None:

    if extension == ".pdf":
        with file_path.open("rb") as file:
            signature = file.read(5)

        if signature != b"%PDF-":
            raise ValueError("Invalid PDF file")

    elif extension == ".docx":
        try:
            with ZipFile(file_path) as archive:
                names = set(archive.namelist())

                if (
                    "word/document.xml" not in names
                    or "[Content_Types].xml" not in names
                ):
                    raise ValueError("Invalid DOCX file")

        except BadZipFile:
            raise ValueError("Invalid DOCX file")

    elif extension == ".txt":
        try:
            content = file_path.read_text(encoding="utf-8")

            if "\x00" in content:
                raise ValueError("Invalid text file")

        except UnicodeDecodeError:
            raise ValueError("Text file must use UTF-8 encoding")


async def save_upload_file(upload: UploadFile) -> tuple[str, str, str, int]:
    original_filename = (upload.filename or "uploaded-file").replace("\\", "/")
    original_filename = Path(original_filename).name[:255]

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX and TXT files are allowed")

    DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_id = uuid4().hex

    stored_filename = f"{file_id}{extension}"

    temporary_path = DOCUMENT_STORAGE_DIR / f".{file_id}.tmp"
    final_path = DOCUMENT_STORAGE_DIR / stored_filename

    file_size = 0

    try:
        with temporary_path.open("wb") as destination:

            while True:
                chunk = await upload.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise ValueError("File size cannot exceed 10 MB")

                destination.write(chunk)

        if file_size == 0:
            raise ValueError("Uploaded file is empty")

        validate_file(temporary_path, extension)

        temporary_path.replace(final_path)

        storage_path = str(
            PurePosixPath("data") / "documents" / stored_filename
        )

        return original_filename, stored_filename, storage_path, file_size

    except Exception:
        temporary_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise


def delete_stored_file(storage_path: str) -> None:

    file_path = (PROJECT_ROOT / storage_path).resolve()

    try:
        file_path.relative_to(DOCUMENT_STORAGE_DIR.resolve())
    except ValueError:
        raise ValueError("Invalid document storage path")

    file_path.unlink(missing_ok=True)