import curses
import importlib.util
import os
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "beets_info", os.path.join(os.path.dirname(__file__), "beets_info.py")
)
if spec and spec.loader:
    beets_info = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(beets_info)
    get_beets_library = beets_info.get_beets_library
else:
    raise ImportError("Could not import beets_info module")


# Configuration
BEETS_LIBRARY = "~/.config/beets/library.db"  # Path to beets library
MUSIC_LIBRARY_ROOT = "/home/davide/Musica"
PHONE_MUSIC_DIR = "/tmp/"  # Mounted phone or remote dir


class MusicSyncTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.artists = []
        self.artist_albums = {}
        self.selected_artist_idx = 0
        self.selected_album_idx = 0
        self.current_view = "artists"  # or "albums"
        self.status_message = ""
        self.load_library()

    def load_library(self):
        """Load artists and albums from beets."""
        try:
            self.artist_albums = get_beets_library()
            self.artists = list(self.artist_albums.keys())
        except Exception as e:
            self.artists = ["Error loading library!"]
            self.artist_albums = {"Error": ["Run 'beet update' first?"]}

    def is_album_on_phone(self, artist, album):
        """Check if album exists on phone."""
        phone_album_path = os.path.join(PHONE_MUSIC_DIR, artist, album)
        return os.path.exists(phone_album_path)

    def toggle_album_sync(self, artist, album):
        """Copy/remove album to/from phone, with error handling and feedback."""
        try:
            src_paths = (
                subprocess.check_output(
                    [
                        "beet",
                        "list",
                        "-af",
                        "$path",
                        f"albumartist:{artist}",
                        f"album:{album}",
                    ],
                    text=True,
                )
                .strip()
                .splitlines()
            )
            album_dirs = (
                subprocess.check_output(
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
                .strip()
                .splitlines()
            )
            album_dir = os.path.abspath(album_dirs[0]) if album_dirs else None
            if not album_dir:
                self.status_message = (
                    f"Could not determine album directory for '{album}'."
                )
                return
            # artist_dir = os.path.dirname(album_dir)
            src_root = MUSIC_LIBRARY_ROOT

            if self.is_album_on_phone(artist, album):
                # Remove album files from phone by relative path
                errors = []
                if not src_paths:
                    self.status_message = f"No source files found for '{album}'."
                    return
                for src_path in src_paths:
                    rel_path = os.path.relpath(src_path, src_root)
                    if rel_path.startswith(".."):
                        errors.append(f"Unsafe rel_path: {rel_path}")
                        continue
                    dest_path = os.path.join(PHONE_MUSIC_DIR, rel_path)
                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                    except Exception as e:
                        errors.append(f"Error removing {dest_path}: {e}")
                if errors:
                    self.status_message = "; ".join(errors)
                else:
                    self.status_message = f"Removed '{album}' from phone."
            else:
                # Sync to phone using relative paths
                if not src_paths:
                    self.status_message = f"No source files found for '{album}'."
                    return
                errors = []
                for src_path in src_paths:
                    # Sanity check: src_path must start with src_root
                    if (
                        not os.path.commonpath([os.path.abspath(src_path), src_root])
                        == src_root
                    ):
                        errors.append(
                            f"src_path {src_path} does not start with src_root {src_root}"
                        )
                        continue
                    rel_path = os.path.relpath(src_path, src_root)
                    if rel_path.startswith(".."):
                        errors.append(
                            f"Unsafe rel_path: {rel_path} (src_path: {src_path}, src_root: {src_root})"
                        )
                        continue
                    dest_path = os.path.join(PHONE_MUSIC_DIR, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    try:
                        result = subprocess.run(["cp", "-r", src_path, dest_path])
                        if result.returncode != 0:
                            errors.append(f"Error copying {src_path}")
                    except Exception as e:
                        errors.append(f"Error copying {src_path}: {e}")
                if errors:
                    self.status_message = "; ".join(errors)
                else:
                    self.status_message = f"Copied '{album}' to phone."
        except Exception as e:
            self.status_message = f"Error: {e}"

    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Title
        title = "Music Sync TUI (Q=Quit, ↑↓=Navigate, Enter=Toggle Sync, R=Refresh)"
        self.stdscr.addstr(0, 0, title[: w - 1], curses.A_BOLD)

        if self.current_view == "artists":
            # List artists
            for idx, artist in enumerate(self.artists):
                if idx + 2 >= h - 1:
                    break
                line = f"{'→' if idx == self.selected_artist_idx else ' '} {artist}"
                self.stdscr.addstr(idx + 2, 0, line[: w - 1])
        else:
            # List albums for selected artist
            artist = self.artists[self.selected_artist_idx]
            albums = self.artist_albums.get(artist, [])

            self.stdscr.addstr(1, 0, f"Artist: {artist}"[: w - 1], curses.A_BOLD)

            for idx, album in enumerate(albums):
                if idx + 3 >= h - 1:
                    break
                status = "[✓]" if self.is_album_on_phone(artist, album) else "[ ]"
                line = (
                    f"{'→' if idx == self.selected_album_idx else ' '} {status} {album}"
                )
                self.stdscr.addstr(idx + 3, 0, line[: w - 1])

        # Show status message at the bottom
        if hasattr(self, "status_message") and self.status_message:
            self.stdscr.addstr(h - 1, 0, self.status_message[: w - 1], curses.A_REVERSE)
        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw()
            key = self.stdscr.getch()

            if key == ord("q"):
                break
            elif key == ord("r"):
                self.load_library()  # Refresh library
            elif key == curses.KEY_UP:
                if self.current_view == "artists":
                    self.selected_artist_idx = max(0, self.selected_artist_idx - 1)
                else:
                    self.selected_album_idx = max(0, self.selected_album_idx - 1)
            elif key == curses.KEY_DOWN:
                if self.current_view == "artists":
                    self.selected_artist_idx = min(
                        len(self.artists) - 1, self.selected_artist_idx + 1
                    )
                else:
                    self.selected_album_idx = min(
                        len(
                            self.artist_albums.get(
                                self.artists[self.selected_artist_idx], []
                            )
                        )
                        - 1,
                        self.selected_album_idx + 1,
                    )
            elif key == curses.KEY_ENTER or key == 10:
                if self.current_view == "artists":
                    self.current_view = "albums"
                else:
                    artist = self.artists[self.selected_artist_idx]
                    album = self.artist_albums[artist][self.selected_album_idx]
                    self.toggle_album_sync(artist, album)
            elif key == curses.KEY_BACKSPACE or key == 27:  # ESC or Backspace
                if self.current_view == "albums":
                    self.current_view = "artists"


def main(stdscr):
    curses.curs_set(0)  # Hide cursor
    app = MusicSyncTUI(stdscr)
    app.run()


if __name__ == "__main__":
    curses.wrapper(main)
