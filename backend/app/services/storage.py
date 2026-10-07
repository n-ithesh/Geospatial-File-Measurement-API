"""File storage service.

Handles persisting uploaded files to disk, cleaning up temporary files,
and providing a safe, sanitised path for each upload.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.errors import FileTooLargeError

logger = logging.getLogger(__name__)


def _ensure_storage_dir() -> Path:
    """Create the storage directory if it does not already exist."""
    storage = settings.STORAGE_DIR
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def sanitise_filename(filename: str) -> str:
    """Return a safe version of the client-supplied filename.

    Only the basename is kept; path separators and control characters are
    stripped so the filename can never escape the upload directory.

    Parameters
    ----------
    filename:
        Raw filename from the ``UploadFile`` object.

    Returns
    -------
    str
        Sanitised filename (basename only, max 255 chars).
    """
    # Take only the basename (handles both POSIX and Windows paths)
    safe = Path(filename).name
    # Replace any remaining path separators and null bytes
    for char in (os.sep, os.altsep, "\x00"):
        if char:
            safe = safe.replace(char, "_")
    safe = safe.strip(". ")[:255] or "upload"
    return safe


import os  # noqa: E402 (needs to be after sanitise_filename uses os.sep)


def save_upload(file_obj: BinaryIO, filename: str, file_id: str) -> Path:
    """Persist an uploaded file to the storage directory.

    The file is stored as ``<STORAGE_DIR>/<file_id>_<sanitised_filename>``
    so the client-supplied name is never used directly as a path.

    Parameters
    ----------
    file_obj:
        The raw file-like object from the ``UploadFile``.
    filename:
        Original (unsanitised) filename from the client.
    file_id:
        UUID string for the associated ``UploadedFile`` DB record.

    Returns
    -------
    Path
        Absolute path of the saved file.

    Raises
    ------
    FileTooLargeError
        If the file exceeds ``settings.max_upload_bytes`` while being written.
    """
    storage = _ensure_storage_dir()
    safe_name = sanitise_filename(filename)
    dest = storage / f"{file_id}_{safe_name}"

    max_bytes = settings.max_upload_bytes
    written = 0
    chunk_size = 1024 * 256  # 256 KB chunks

    logger.info("Saving upload to %s (limit=%d bytes)", dest, max_bytes)

    with open(dest, "wb") as out:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise FileTooLargeError(
                    f"File exceeds the maximum upload size of {settings.MAX_UPLOAD_MB} MB."
                )
            out.write(chunk)

    logger.info("Saved %d bytes to %s", written, dest)
    return dest


def delete_file(path: Path) -> None:
    """Delete a file from disk, logging but not re-raising on errors.

    Parameters
    ----------
    path:
        Path to the file to remove.
    """
    try:
        path.unlink(missing_ok=True)
        logger.info("Deleted file: %s", path)
    except Exception:
        logger.warning("Failed to delete file: %s", path, exc_info=True)


def delete_upload_dir(file_id: str) -> None:
    """Remove all files in the storage directory that belong to *file_id*.

    Parameters
    ----------
    file_id:
        UUID of the uploaded file whose artefacts should be deleted.
    """
    storage = settings.STORAGE_DIR
    if not storage.exists():
        return
    pattern = f"{file_id}_*"
    for p in storage.glob(pattern):
        delete_file(p)
