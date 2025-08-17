import os

import psutil
from textual import on, work
from textual.app import ComposeResult, Widget
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import Label, ListItem, ListView
from textual_fspicker import SelectDirectory


def get_accessible_subdir(mount):
    candidates = [
        os.path.join(mount, "storage", "emulated", "0"),
        os.path.join(mount, "Internal Storage"),
        mount,
    ]
    for path in candidates:
        if os.path.isdir(path) and os.access(path, os.R_OK | os.X_OK):
            return path
    return mount


class MountAndFolderPicker(Screen[str]):
    class DirectoryPicked:
        def __init__(self, path):
            self.path = path

    def __init__(self):
        super().__init__()
        self.mounts = [
            part.mountpoint
            for part in psutil.disk_partitions(all=True)
            if part.fstype and part.mountpoint.startswith("/run/user/")
        ]
        self.list_view = ListView(*[ListItem(Label(mount)) for mount in self.mounts])
        self.selected_mount = None
        self.directory_picker = None
        self.selected_path = None

    def compose(self) -> ComposeResult:
        yield Label("Select a mount point:")
        yield self.list_view

    @on(ListView.Selected)
    @work
    async def on_mount_selected(self, event: ListView.Selected):
        self.selected_mount = event.item.query_one(Label).renderable
        accessible_root = get_accessible_subdir(self.selected_mount)
        directory = await self.app.push_screen_wait(
            SelectDirectory(location=accessible_root)
        )
        self.dismiss(directory)
