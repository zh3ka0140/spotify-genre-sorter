"""
Create private "Genre: <name>" playlists from song_genres.csv and add the songs.
Safe: never edits or deletes anything you already have; re-running adds only songs
that are not already in the genre playlist.  Use --dry to preview without creating.
"""
import csv, os, sys
import spotipy
from spotipy.oauth2 import SpotifyPKCE

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

dry = "--dry" in sys.argv
include_unsorted = "--include-unsorted" in sys.argv
rows = list(csv.DictReader(open("song_genres.csv", encoding="utf-8")))
plan = {}
for r in rows:
    if not r["uri"] or (r["bucket"] == "Unsorted" and not include_unsorted):
        continue
    plan.setdefault(r["bucket"], []).append(r["uri"])
for b, u in sorted(plan.items(), key=lambda kv: -len(kv[1])):
    print(f"{len(u):5d}  Genre: {b}")
if dry:
    print("\nDry run only - nothing created."); sys.exit()

sp = spotipy.Spotify(auth_manager=SpotifyPKCE(
    scope="playlist-modify-private playlist-read-private"), requests_timeout=30, retries=5)
me = sp.current_user()["id"]
existing = {}
page = sp.current_user_playlists(limit=50)
while page:
    for p in page["items"]:
        if p["owner"]["id"] == me: existing[p["name"]] = p["id"]
    page = sp.next(page) if page.get("next") else None

for b, uris in plan.items():
    name = "Genre: " + b
    pid = existing.get(name) or sp.user_playlist_create(me, name, public=False,
                                  description="Sorted by genre")["id"]
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(pid, uris[i:i+100])
    print(f"  {name}: added {len(uris)}")
print("Done.")
