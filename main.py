from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Horizontal, Vertical

import asyncio
import core


class MusicSyncApp(App):
    CSS = """
    Horizontal {
        height: 1fr;
    }
    ListView {
        width: 1fr;
        border: solid gray;
    }
    """

    def __init__(self):
        super().__init__()
        self.library = {}
        self.selected_artist: str | None = None
        self.status_cache: dict[tuple[str, str], bool] = {}

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Label("Artists", id="artists_label"),
                ListView(id="artists_list"),
            ),
            Vertical(
                Label("Albums", id="albums_label"),
                ListView(id="albums_list"),
            ),
        )

    async def on_mount(self):
        self.library = core.get_library()
        artists = list(self.library.keys())
        artists_list = self.query_one("#artists_list", ListView)
        for artist in artists:
            artists_list.append(ListItem(Label(artist)))
        artists_list.index = 0
        artists_list.focus()
        # show first artist's albums immediately
        if artists:
            self.selected_artist = artists[0]
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library[self.selected_artist]:
                status = "[✓]" if self.status_cache.get((self.selected_artist, album), False) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))
            albums_list.index = 0
        # highlight first artist on mount
        self.post_message(ListView.Highlighted(artists_list, artists_list.children[0]))
        asyncio.create_task(self._load_statuses())

    def on_list_view_selected(self, event: ListView.Selected):
        view_id = event.list_view.id
        item_label = event.item.query_one(Label).renderable
        if view_id == "artists_list":
            self.selected_artist = item_label
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(self.selected_artist, []):
                status = "[✓]" if self.status_cache.get((self.selected_artist, album), False) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))
            albums_list.index = 0
            albums_list.index = 0
            albums_list.focus()
            # highlight first album on artist select
            self.post_message(ListView.Highlighted(albums_list, albums_list.children[0]))
        elif view_id == "albums_list" and self.selected_artist:
            parts = item_label.split(" ", 2)
            album = parts[-1]
            if self.status_cache.get((self.selected_artist, album), False):
                core.unsync_album(self.selected_artist, album)
            else:
                core.sync_album(self.selected_artist, album)
            self.status_cache[(self.selected_artist, album)] = core.is_album_synced(self.selected_artist, album)
            # refresh album list
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(self.selected_artist, []):
                status = "[✓]" if self.status_cache.get((self.selected_artist, album), False) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        try:
            artist = event.item.query_one(Label).renderable
        except Exception:
            return
        try:
            artist = event.item.query_one(Label).renderable
        except Exception:
            return
        if event.list_view.id == "artists_list":
            artist = event.item.query_one(Label).renderable
            self.selected_artist = artist
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(artist, []):
                status = "[✓]" if self.status_cache.get((artist, album), False) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))

    async def _load_statuses(self):
        for artist, albums in self.library.items():
            for album in albums:
                status = await asyncio.to_thread(core.is_album_synced, artist, album)
                self.status_cache[(artist, album)] = status
                if self.selected_artist == artist:
                    albums_list = self.query_one("#albums_list", ListView)
                    for item in albums_list.children:
                        try:
                            label = item.query_one(Label)
                        except Exception:
                            continue
                        text = label.renderable
                        if text.endswith(album):
                            prefix = "[✓]" if status else "[ ]"
                            label.update(f"{prefix} {album}")


def main():
    MusicSyncApp().run()


if __name__ == "__main__":
    main()
