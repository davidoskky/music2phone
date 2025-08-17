import os
import shutil
import subprocess
from typing import Dict, List

from beets_info import get_beets_library


def get_beets_library_root() -> str:
    config = subprocess.check_output(["beet", "config", "-d"], text=True)
    for line in config.splitlines():
        if line.strip().startswith("directory:"):
            value = line.split(":", 1)[1].strip()
            return os.path.expanduser(value)
    raise RuntimeError("Could not find 'directory' in beets config")


def get_library() -> Dict[str, List[str]]:
    return get_beets_library()


_album_file_cache: Dict[tuple[str, str], List[str]] = {}

def build_album_file_cache() -> None:
    library_root = get_beets_library_root()
    output = subprocess.check_output(
        ["beet", "list", "-af", "$path|$albumartist|$album"], text=True
    )
    for line in output.splitlines():
        src_path, artist, album = line.split("|", 2)
        rel_path = os.path.relpath(src_path, library_root)
        _album_file_cache.setdefault((artist, album), []).append(rel_path)


def get_album_paths(artist: str, album: str) -> List[str]:
    rels = _album_file_cache.get((artist, album), [])
    library_root = get_beets_library_root()
    return [os.path.join(library_root, rel) for rel in rels]


def get_album_dir(artist: str, album: str) -> str:
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
    rels = _album_file_cache.get((artist, album), [])
    if not rels:
        return False
    for rel_path in rels:
        phone_path = os.path.join(phone_dir, rel_path)
        if not os.path.exists(phone_path):
            return False
    return True


def sync_album(phone_dir: str, artist: str, album: str) -> str:
    library_root = get_beets_library_root()
    rels = _album_file_cache.get((artist, album), [])
    if not rels:
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for rel_path in rels:
        if rel_path.startswith(".."):
            errors.append(f"Unsafe rel_path: {rel_path}")
            continue
        src_path = os.path.join(library_root, rel_path)
        dest_path = os.path.join(phone_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        result = subprocess.run(["cp", "-r", src_path, dest_path])
        if result.returncode != 0:
            errors.append(f"Error copying {src_path}")
    if errors:
        return "; ".join(errors)
    return f"Copied '{album}' to phone."


def unsync_album(phone_dir: str, artist: str, album: str) -> str:
    library_root = get_beets_library_root()
    rels = _album_file_cache.get((artist, album), [])
    if not rels:
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for rel_path in rels:
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
