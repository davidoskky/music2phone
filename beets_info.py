import subprocess
from typing import Dict, List


def get_beets_library() -> Dict[str, List[str]]:
    """Return a dict mapping artists to their albums using beets CLI (fast version)."""
    try:
        output = subprocess.check_output(
            ["beet", "list", "-a", "-f", "$albumartist\t$album"], text=True
        )
        artist_albums = {}
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            artist, album = line.split("\t", 1)
            artist_albums.setdefault(artist, set()).add(album)
        # Convert sets to sorted lists
        return {artist: sorted(list(albums)) for artist, albums in artist_albums.items()}
    except Exception as e:
        return {"Error": [f"Error loading library: {e}"]}
