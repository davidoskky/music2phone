import curses
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

# dynamic import core module
spec = importlib.util.spec_from_file_location(
    "core", os.path.join(os.path.dirname(__file__), "core.py")
)
if spec and spec.loader:
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
else:
    raise ImportError("Could not import core module")


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
        self.artist_scroll = 0
        self.album_scroll = 0
        self.current_view = "artists"  # or "albums"
        self.status_message = ""
        self.load_library()

    def load_library(self):
        """Load artists and albums from beets."""
        try:
            self.artist_albums = core.get_library()
            self.artists = list(self.artist_albums.keys())
        except Exception as e:
            self.artists = ["Error loading library!"]
            self.artist_albums = {"Error": ["Run 'beet update' first?"]}

    def is_album_on_phone(self, artist, album):
        """Check if all album files exist on phone."""
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
            for src_path in src_paths:
                rel_path = os.path.relpath(src_path, MUSIC_LIBRARY_ROOT)
                phone_path = os.path.join(PHONE_MUSIC_DIR, rel_path)
                if not os.path.exists(phone_path):
                    return False
            return True if src_paths else False
        except Exception:
            return False

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
                        if os.path.isfile(dest_path):
                            os.remove(dest_path)
                        elif os.path.isdir(dest_path):
                            import shutil

                            shutil.rmtree(dest_path)
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
            max_visible = h - 3
            start = self.artist_scroll
            end = min(len(self.artists), start + max_visible)
            for idx, artist in enumerate(self.artists[start:end], start=start):
                line = f"{'→' if idx == self.selected_artist_idx else ' '} {artist}"
                self.stdscr.addstr(idx - start + 2, 0, line[: w - 1])
        else:
            # List albums for selected artist
            artist = self.artists[self.selected_artist_idx]
            albums = self.artist_albums.get(artist, [])

            self.stdscr.addstr(1, 0, f"Artist: {artist}"[: w - 1], curses.A_BOLD)

            max_visible = h - 3
            start = self.album_scroll
            end = min(len(albums), start + max_visible)
            for idx, album in enumerate(albums[start:end], start=start):
                status = "[✓]" if self.is_album_on_phone(artist, album) else "[ ]"
                line = (
                    f"{'→' if idx == self.selected_album_idx else ' '} {status} {album}"
                )
                self.stdscr.addstr(idx - start + 3, 0, line[: w - 1])

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
                    max_visible = self.stdscr.getmaxyx()[0] - 3
                    if self.selected_artist_idx < self.artist_scroll:
                        self.artist_scroll = self.selected_artist_idx
                    elif self.selected_artist_idx >= self.artist_scroll + max_visible:
                        self.artist_scroll = self.selected_artist_idx - max_visible + 1
                else:
                    self.selected_album_idx = max(0, self.selected_album_idx - 1)
                    max_visible = self.stdscr.getmaxyx()[0] - 3
                    if self.selected_album_idx < self.album_scroll:
                        self.album_scroll = self.selected_album_idx
                    elif self.selected_album_idx >= self.album_scroll + max_visible:
                        self.album_scroll = self.selected_album_idx - max_visible + 1
            elif key == curses.KEY_DOWN:
                if self.current_view == "artists":
                    self.selected_artist_idx = min(
                        len(self.artists) - 1, self.selected_artist_idx + 1
                    )
                    max_visible = self.stdscr.getmaxyx()[0] - 3
                    if self.selected_artist_idx < self.artist_scroll:
                        self.artist_scroll = self.selected_artist_idx
                    elif self.selected_artist_idx >= self.artist_scroll + max_visible:
                        self.artist_scroll = self.selected_artist_idx - max_visible + 1
                else:
                    album_list = self.artist_albums.get(
                        self.artists[self.selected_artist_idx], []
                    )
                    self.selected_album_idx = min(
                        len(album_list) - 1, self.selected_album_idx + 1
                    )
                    max_visible = self.stdscr.getmaxyx()[0] - 3
                    if self.selected_album_idx < self.album_scroll:
                        self.album_scroll = self.selected_album_idx
                    elif self.selected_album_idx >= self.album_scroll + max_visible:
                        self.album_scroll = self.selected_album_idx - max_visible + 1
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
