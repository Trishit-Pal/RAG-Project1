"""Save files that people upload in the browser, safely.

Used by the Upload page (saving) and the Data page (listing CSV files).
The upload size limit is set in .streamlit/config.toml; Streamlit refuses
bigger files before they reach this code.
"""
from pathlib import Path

from core.ingest import SUPPORTED_TYPES

UPLOAD_DIR = Path("data/uploads")


def save_upload(filename: str, data: bytes, folder: Path = UPLOAD_DIR) -> Path:
    """Write the uploaded file to the upload folder and return where it was saved.

    Raises ValueError with a friendly message if the file should not be accepted.
    """
    # .name drops any folder part, so "../../x.csv" becomes "x.csv" and cannot
    # be written outside the upload folder.
    safe_name = Path(filename).name
    extension = Path(safe_name).suffix.lower()

    if extension not in SUPPORTED_TYPES:
        raise ValueError(f"'{safe_name}': this file type is not supported (use {', '.join(SUPPORTED_TYPES)})")
    if not data:
        raise ValueError(f"'{safe_name}' is empty")

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    # Never silently replace a different file: the Data page reads files from this folder.
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"A different file named '{safe_name}' already exists. Rename your file and try again.")
    path.write_bytes(data)
    return path


def remove_upload(path: Path) -> None:
    # Used for files that were set aside, so they do not show up on the Data page.
    path.unlink(missing_ok=True)


def list_saved_csvs(folder: Path = UPLOAD_DIR) -> list[Path]:
    # The Data page reads the original CSVs, because the database only holds row text.
    if not folder.exists():
        return []
    return sorted(folder.glob("*.csv"))
