"""
Spotify Playlist Sorter FULL
Sorts your Liked Songs AND every playlist (yours, saved from others, Spotify-made) into
private "Genre: <name>" playlists, one niche genre per song, no repeats.

Why a second script: Spotify's API no longer lets a normal app read the songs inside
playlists, so this version gets playlist contents from a file instead:
  * playlists_scraped.json   made by scrape_playlists.js in the Spotify web player
                             (works for ALL playlists in your library), and/or
  * Playlist1.json           from Spotify's "Download your data" export (your own playlists)
Liked Songs are still read through the API.

Steps (one command):  python spotify_playlist_sorter_full.py
  1. collect   Liked Songs + playlist files -> preview_songs.csv (duplicates removed)
  2. lookup    runs lookup_genres.py (MusicBrainz genres per artist, resumable)
  3. create    previews, asks YES, then runs create_playlists_from_csv.py

Options:
  --no-liked           skip the API and use only the playlist files
  --playlists FILE...  playlist files to read (default: playlists_scraped.json and
                       Playlist1.json when they exist)
  --collect-only       stop after step 1
  --skip-lookup        reuse an existing song_genres.csv
  --yes                do not ask before creating playlists
Nothing in Spotify is edited or deleted, and your Liked Songs are never changed.
"""
import csv, json, os, subprocess, sys

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

args = sys.argv[1:]
def flag(n): return n in args
files = []
if "--playlists" in args:
    i = args.index("--playlists") + 1
    while i < len(args) and not args[i].startswith("--"):
        files.append(args[i]); i += 1
else:
    files = [f for f in ("playlists_scraped.json", "Playlist1.json") if os.path.exists(f)]

songs = {}   # uri -> dict(song, artists, found_in=set())

def add(uri, song, artists, source):
    if not uri: return
    d = songs.setdefault(uri, {"song": song or "", "artists": artists or "", "found_in": []})
    if source not in d["found_in"]: d["found_in"].append(source)
    if song and not d["song"]: d["song"] = song
    if artists and not d["artists"]: d["artists"] = artists

# ---- Liked Songs through the API -------------------------------------------------
if not flag("--no-liked"):
    import spotipy
    from spotipy.oauth2 import SpotifyPKCE
    sp = spotipy.Spotify(auth_manager=SpotifyPKCE(scope="user-library-read"),
                         requests_timeout=30, retries=5)
    page = sp.current_user_saved_tracks(limit=50)
    while page:
        for it in page["items"]:
            t = it["track"]
            add(t["uri"], t["name"], ", ".join(a["name"] for a in t["artists"]), "Liked Songs")
        page = sp.next(page) if page.get("next") else None
    print(f"Liked Songs: {len(songs)} songs")

# ---- Playlist files --------------------------------------------------------------
for path in files:
    data = json.load(open(path, encoding="utf-8"))
    n0 = len(songs)
    if isinstance(data, dict) and "playlists" in data:           # Spotify data export
        for pl in data["playlists"]:
            for it in pl.get("items", []):
                t = it.get("track") or {}
                add(t.get("trackUri"), t.get("trackName"), t.get("artistName"), pl.get("name", "playlist"))
    else:                                                          # scrape_playlists.js output
        for key, tracks in data.items():
            name = key.split("||")[0]
            for tid, (title, artists) in tracks:
                add("spotify:track:" + tid, title, artists, name)
    print(f"{path}: {len(songs) - n0} new songs")

print(f"Total distinct songs: {len(songs)}")
# Songs that an earlier run already put in a genre playlist are left alone, so every song
# stays in exactly one playlist even when you run this again after adding new music.
if os.path.exists("created_state.json"):
    done = {u for uris in json.load(open("created_state.json", encoding="utf-8")).values() for u in uris}
    before = len(songs)
    songs = {u: d for u, d in songs.items() if u not in done}
    print(f"Skipping {before - len(songs)} songs already placed by earlier runs; {len(songs)} new")
with open("preview_songs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["bucket", "song", "artists", "spotify_genres", "found_in", "uri"])
    for uri, d in songs.items():
        w.writerow(["Unsorted", d["song"], d["artists"], "", " | ".join(d["found_in"]), uri])
print("Wrote preview_songs.csv")
if flag("--collect-only"): sys.exit()

py = sys.executable
if not flag("--skip-lookup"):
    print("\nLooking up genres (resumable, a few seconds per new artist)...")
    subprocess.run([py, "lookup_genres.py"], check=True)

print("\nPreview of playlists that would be created:")
subprocess.run([py, "create_playlists_from_csv.py", "--dry"], check=True)
if not flag("--yes"):
    if input("\nType YES to create these private playlists in Spotify: ").strip().upper() != "YES":
        print("Cancelled."); sys.exit()
subprocess.run([py, "create_playlists_from_csv.py"], check=True)
