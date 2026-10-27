"""Set every playlist named "Genre: ..." that you own to private."""
import sys
import spotipy
from spotipy.oauth2 import SpotifyPKCE
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sp = spotipy.Spotify(auth_manager=SpotifyPKCE(
    scope="playlist-modify-private playlist-modify-public playlist-read-private"),
    requests_timeout=30, retries=5)
me = sp.current_user()["id"]
n = 0
page = sp.current_user_playlists(limit=50)
while page:
    for p in page["items"]:
        if p["owner"]["id"] == me and p["name"].startswith("Genre: "):
            try:
                sp._put(f"playlists/{p['id']}", payload={"public": False})
                n += 1
                print("private:", p["name"])
            except Exception as e:
                print("FAILED:", p["name"], e)
    page = sp.next(page) if page.get("next") else None
print(f"Done. {n} playlists set to private.")
