"""Save files that people upload in the browser, safely."""
from pathlib import Path

from core.ingest import SUPPORTED_TYPES

UPLOAD_DIR = Path("data/uploads")
# The size limit lives in .streamlit/config.toml (maxUploadSize). Streamlit
# refuses bigger files before they reach this code.


def save_upload(filename: str, data: bytes, folder: Path = UPLOAD_DIR) -> Path:
    """Write the uploaded bytes to the upload folder and return the saved path.

    Raises ValueError with a friendly message if the file should not be accepted.
    """
    # Path(...).name drops any folders, so "../../x.csv" becomes "x.csv".
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()

    if suffix not in SUPPORTED_TYPES:
        raise ValueError(f"'{safe_name}': this file type is not supported (use {', '.join(sorted(SUPPORTED_TYPES))})")
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

