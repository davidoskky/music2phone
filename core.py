import os
import shutil
import subprocess
from typing import Dict, List

from beets_info import get_beets_library

def debug_log(msg):
    with open("debug.log", "a") as f:
        f.write(msg + "\n")

def get_beets_library_root() -> str:
    config = subprocess.check_output(["beet", "config", "-d"], text=True)
    for line in config.splitlines():
        if line.strip().startswith("directory:"):
            value = line.split(":", 1)[1].strip()
            return os.path.expanduser(value)
    raise RuntimeError("Could not find 'directory' in beets config")

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
    music_library_root = get_beets_library_root()
    debug_log(f"is_album_synced: phone_dir={phone_dir}, artist={artist}, album={album}, music_library_root={music_library_root}")
    paths = get_album_paths(artist, album)
    if not paths:
        debug_log("No album paths found.")
        return False
    for src_path in paths:
        rel_path = os.path.relpath(src_path, music_library_root)
        phone_path = os.path.join(phone_dir, rel_path)
        debug_log(f"Checking: {phone_path}")
        if not os.path.exists(phone_path):
            debug_log(f"Missing: {phone_path}")
            return False
    return True


def sync_album(phone_dir: str, artist: str, album: str) -> str:
    music_library_root = get_beets_library_root()
    debug_log(f"sync_album: phone_dir={phone_dir}, artist={artist}, album={album}, music_library_root={music_library_root}")
    paths = get_album_paths(artist, album)
    if not paths:
        debug_log(f"No source files found for '{album}'.")
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for src_path in paths:
        rel_path = os.path.relpath(src_path, music_library_root)
        if rel_path.startswith(".."):
            errors.append(f"Unsafe rel_path: {rel_path}")
            debug_log(f"Unsafe rel_path: {rel_path}")
            continue
        dest_path = os.path.join(phone_dir, rel_path)
        debug_log(f"Copying {src_path} -> {dest_path}")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        result = subprocess.run(["cp", "-r", src_path, dest_path])
        if result.returncode != 0:
            errors.append(f"Error copying {src_path}")
            debug_log(f"Error copying {src_path}")
    if errors:
        return "; ".join(errors)
    return f"Copied '{album}' to phone."


def unsync_album(phone_dir: str, artist: str, album: str) -> str:
    music_library_root = get_beets_library_root()
    debug_log(f"unsync_album: phone_dir={phone_dir}, artist={artist}, album={album}, music_library_root={music_library_root}")
    paths = get_album_paths(artist, album)
    if not paths:
        debug_log(f"No source files found for '{album}'.")
        return f"No source files found for '{album}'."
    errors: List[str] = []
    for src_path in paths:
        rel_path = os.path.relpath(src_path, music_library_root)
        if rel_path.startswith(".."):
            errors.append(f"Unsafe rel_path: {rel_path}")
            debug_log(f"Unsafe rel_path: {rel_path}")
            continue
        dest_path = os.path.join(phone_dir, rel_path)
        debug_log(f"Removing {dest_path}")
        try:
            if os.path.isfile(dest_path):
                os.remove(dest_path)
            elif os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
        except Exception as e:
            errors.append(f"Error removing {dest_path}: {e}")
            debug_log(f"Error removing {dest_path}: {e}")
    if errors:
        return "; ".join(errors)
    return f"Removed '{album}' from phone."
