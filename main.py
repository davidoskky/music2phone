from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Horizontal, Vertical

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

    def on_mount(self):
        self.library = core.get_library()
        artists = list(self.library.keys())
        artists_list = self.query_one("#artists_list", ListView)
        for artist in artists:
            artists_list.append(ListItem(Label(artist)))
        artists_list.focus()

    def on_list_view_selected(self, event: ListView.Selected):
        view_id = event.list_view.id
        item_label = event.item.query_one(Label).renderable
        if view_id == "artists_list":
            self.selected_artist = item_label
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(self.selected_artist, []):
                status = "[✓]" if core.is_album_synced(self.selected_artist, album) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))
            albums_list.focus()
        elif view_id == "albums_list" and self.selected_artist:
            parts = item_label.split(" ", 2)
            album = parts[-1]
            if core.is_album_synced(self.selected_artist, album):
                core.unsync_album(self.selected_artist, album)
            else:
                core.sync_album(self.selected_artist, album)
            # refresh album list
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(self.selected_artist, []):
                status = "[✓]" if core.is_album_synced(self.selected_artist, album) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))
    def on_list_view_highlighted(self, event: ListView.Highlighted):
        if event.list_view.id == "artists_list":
            artist = event.item.query_one(Label).renderable
            self.selected_artist = artist
            albums_list = self.query_one("#albums_list", ListView)
            albums_list.clear()
            for album in self.library.get(artist, []):
                status = "[✓]" if core.is_album_synced(artist, album) else "[ ]"
                albums_list.append(ListItem(Label(f"{status} {album}")))



def main():
    MusicSyncApp().run()


if __name__ == "__main__":
    main()
