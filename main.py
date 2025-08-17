import curses
import importlib.util
import os

# dynamic import core module
spec = importlib.util.spec_from_file_location(
    "core", os.path.join(os.path.dirname(__file__), "core.py")
)
if spec and spec.loader:
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
else:
    raise ImportError("Could not import core module")


class MusicSyncTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.artists = []
        self.artist_albums = {}
        self.selected_artist_idx = 0
        self.selected_album_idx = 0
        self.artist_scroll = 0
        self.album_scroll = 0
        self.current_view = "artists"
        self.status_message = ""
        self.load_library()

    def load_library(self):
        try:
            self.artist_albums = core.get_library()
            self.artists = list(self.artist_albums.keys())
        except Exception:
            self.artists = ["Error loading library!"]
            self.artist_albums = {"Error": ["Run 'beet update' first?"]}

    def is_album_on_phone(self, artist, album):
        return core.is_album_synced(artist, album)

    def toggle_album_sync(self, artist, album):
        if core.is_album_synced(artist, album):
            self.status_message = core.unsync_album(artist, album)
        else:
            self.status_message = core.sync_album(artist, album)

    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        title = "Music Sync TUI (Q=Quit, ↑↓=Navigate, Enter=Toggle Sync, R=Refresh)"
        self.stdscr.addstr(0, 0, title[: w - 1], curses.A_BOLD)

        if self.current_view == "artists":
            max_visible = h - 3
            start = self.artist_scroll
            end = min(len(self.artists), start + max_visible)
            for idx, artist in enumerate(self.artists[start:end], start=start):
                line = f"{'→' if idx == self.selected_artist_idx else ' '} {artist}"
                self.stdscr.addstr(idx - start + 2, 0, line[: w - 1])
        else:
            artist = self.artists[self.selected_artist_idx]
            albums = self.artist_albums.get(artist, [])
            self.stdscr.addstr(1, 0, f"Artist: {artist}"[: w - 1], curses.A_BOLD)
            max_visible = h - 3
            start = self.album_scroll
            end = min(len(albums), start + max_visible)
            for idx, album in enumerate(albums[start:end], start=start):
                status = "[✓]" if core.is_album_synced(artist, album) else "[ ]"
                line = f"{'→' if idx == self.selected_album_idx else ' '} {status} {album}"
                self.stdscr.addstr(idx - start + 3, 0, line[: w - 1])

        if self.status_message:
            self.stdscr.addstr(h - 1, 0, self.status_message[: w - 1], curses.A_REVERSE)
        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw()
            key = self.stdscr.getch()
            if key == ord("q"):
                break
            elif key == ord("r"):
                self.load_library()
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
            elif key in (curses.KEY_ENTER, 10):
                if self.current_view == "artists":
                    self.current_view = "albums"
                else:
                    artist = self.artists[self.selected_artist_idx]
                    album = self.artist_albums[artist][self.selected_album_idx]
                    self.toggle_album_sync(artist, album)
            elif key in (curses.KEY_BACKSPACE, 27):
                if self.current_view == "albums":
                    self.current_view = "artists"

def main(stdscr):
    curses.curs_set(0)
    app = MusicSyncTUI(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)
