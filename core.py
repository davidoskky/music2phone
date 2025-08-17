import os
import shutil
import subprocess
from typing import Dict, List

from beets_info import get_beets_library
from config import MUSIC_LIBRARY_ROOT, PHONE_MUSIC_DIR


def get_library() -> Dict[str, List[str]]:
    """Return the mapping of artists to albums from beets library."""
    return get_beets_library()


def get_album_paths(artist: str, album: str) -> List[str]:
    """Return list of file paths for the given album from beets."""
    output = subprocess.check_output(
        ["beet", "list", "-af", "$path", f"albumartist:{artist}", f"album:{album}"],
        text=True,
    )
    return output.strip().splitlines()


def get_album_dir(artist: str, album: str) -> str:
    """Return the album directory path from beets."""
    output = subprocess.check_output(
        [
            "beet",
            "list",
            "-af",
            "$albumpath",
            f"albumartist:{artist}",
            f"album:{album}",
        ],
        text=True,
    )
    dirs = output.strip().splitlines()
    return os.path.abspath(dirs[0]) if dirs else ""


def is_album_synced(phone_dir: str, artist: str, album: str) -> bool:
    """Check if all album files are present on the phone."""
    paths = get_album_paths(artist, album)
    if not paths:
        return False
    for src_path in paths:
        rel_path = os.path.relpath(src_path, MUSIC_LIBRARY_ROOT)
        phone_path = os.path.join(phone_dir, rel_path)
        if not os.path.exists(phone_path):
            return False
    return True


def sync_album(phone_dir: str, artist: str, album: str) -> str:
    """Sync album files to phone, preserving relative structure."""
    paths = get_album_paths(artist, album)
    if not paths:
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for src_path in paths:
        rel_path = os.path.relpath(src_path, MUSIC_LIBRARY_ROOT)
        if rel_path.startswith(".."):
            errors.append(f"Unsafe rel_path: {rel_path}")
            continue
        dest_path = os.path.join(phone_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        result = subprocess.run(["cp", "-r", src_path, dest_path])
        if result.returncode != 0:
            errors.append(f"Error copying {src_path}")
    if errors:
        return "; ".join(errors)
    return f"Copied '{album}' to phone."


def unsync_album(phone_dir: str, artist: str, album: str) -> str:
    """Remove synced album files from phone."""
    paths = get_album_paths(artist, album)
    if not paths:
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for src_path in paths:
        rel_path = os.path.relpath(src_path, MUSIC_LIBRARY_ROOT)
        if rel_path.startswith(".."):
            errors.append(f"Unsafe rel_path: {rel_path}")
            continue
        dest_path = os.path.join(phone_dir, rel_path)
        try:
            if os.path.isfile(dest_path):
                os.remove(dest_path)
            elif os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
        except Exception as e:
            errors.append(f"Error removing {dest_path}: {e}")
    if errors:
        return "; ".join(errors)
    return f"Removed '{album}' from phone."

