import os

import psutil
from textual import on, work
from textual.app import ComposeResult, Widget
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView
from textual_fspicker import SelectDirectory


def debug_log(msg):
    with open("debug.log", "a") as f:
        f.write(msg + "\n")


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


class MountAndFolderPicker(Widget):
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
        debug_log("MountAndFolderPicker: Initiated mount picker")

    def compose(self) -> ComposeResult:
        debug_log("MountAndFolderPicker: Composing mount list")
        yield Label("Select a mount point:")
        yield self.list_view

    @on(ListView.Selected)
    @work
    async def on_mount_selected(self, event: ListView.Selected):
        try:
            self.selected_mount = event.item.query_one(Label).renderable
            debug_log(f"User selected mount: {self.selected_mount}")
            accessible_root = get_accessible_subdir(self.selected_mount)
            debug_log(f"Using accessible root: {accessible_root}")
            directory = await self.app.push_screen_wait(
                SelectDirectory(location=accessible_root)
            )
            debug_log(f"Got Directory: {directory}")
            self.on_folder_selected(directory)
        except Exception as e:
            debug_log(f"Exception in on_mount_selected: {e}")

    def on_folder_selected(self, path):
        try:
            debug_log(f"MountAndFolderPicker: Folder selected: {path}")
            self.selected_path = str(path)
            self.app.post_message(self.DirectoryPicked(self.selected_path))
        except Exception as e:
            debug_log(f"Exception in on_folder_selected: {e}")
